[CmdletBinding()]
param(
    [switch]$ValidateMt5Only,
    [ValidateRange(5, 60)]
    [int]$PublicDataTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$Distro = "Ubuntu-ODIN"
$StatePath = "D:\ODIN_LOCAL\state\autonomous_demo_state.json"
$HeartbeatPath = "D:\ODIN_LOCAL\state\autonomous_demo_heartbeat.json"
$ExpectedBroker = "OANDA TMS Brokers S.A."
$ExpectedServer = "OANDATMS-MT5"
$ExpectedTerminal = "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe"

function Assert-ODINHardwareSafe {
    $gpuCommand = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
    if ($null -eq $gpuCommand) { $gpuCommand = Get-Command nvidia-smi -ErrorAction SilentlyContinue }
    if ($null -eq $gpuCommand) { throw "GPU temperature telemetry is unavailable; collection is blocked." }
    $gpuReading = & $gpuCommand.Source --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>$null | Select-Object -First 1
    $gpuTemp = 0
    if (-not [int]::TryParse(([string]$gpuReading).Trim(), [ref]$gpuTemp)) { throw "GPU temperature telemetry is invalid; collection is blocked." }
    if ($gpuTemp -ge 80) { throw "GPU temperature is ${gpuTemp}C; collection is blocked." }

    $cpuSensors = @(Get-CimInstance -Namespace root/WMI -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue)
    $cpuTemps = @($cpuSensors | ForEach-Object { [math]::Round(($_.CurrentTemperature / 10.0) - 273.15, 1) })
    if (@($cpuTemps | Where-Object { $_ -ge 80 }).Count -gt 0) { throw "CPU temperature is at least 80C; collection is blocked." }
    Write-Output "Hardware guard: GPU ${gpuTemp}C; CPU telemetry $(if ($cpuTemps.Count) { $cpuTemps -join ',' } else { 'unavailable' })."
}

function Assert-ODINAutonomousDemoObservation {
    if (-not (Test-Path -LiteralPath $StatePath) -or -not (Test-Path -LiteralPath $HeartbeatPath)) {
        throw "The persistent OANDA DEMO observation is unavailable."
    }
    try {
        $state = Get-Content -Raw -LiteralPath $StatePath | ConvertFrom-Json
        $heartbeat = Get-Content -Raw -LiteralPath $HeartbeatPath | ConvertFrom-Json
        $heartbeatAt = [DateTimeOffset]::Parse([string]$heartbeat.heartbeat_at_utc)
    }
    catch {
        throw "The persistent OANDA DEMO observation is invalid."
    }
    $observed = $state.observed
    if (
        $observed.account_mode -ne "DEMO" -or
        $observed.broker -ne $ExpectedBroker -or
        $observed.server -ne $ExpectedServer -or
        $observed.terminal_path -ne $ExpectedTerminal -or
        $observed.terminal_connected -ne $true
    ) {
        throw "The persistent OANDA DEMO identity is blocked."
    }
    if (
        $state.safe_to_trade -ne $false -or
        $state.real_trading -ne $false -or
        $state.execution_allowed -ne $false -or
        $observed.broker_submission_called -ne $false
    ) {
        throw "The persistent OANDA DEMO guardrails are invalid."
    }
    $heartbeatAge = ([DateTimeOffset]::UtcNow - $heartbeatAt).TotalSeconds
    if ($heartbeatAge -lt 0 -or $heartbeatAge -gt 120) {
        throw "The persistent OANDA DEMO heartbeat is stale or future-dated."
    }
    if ($null -eq (Get-Process -Id ([int]$heartbeat.process_id) -ErrorAction SilentlyContinue)) {
        throw "The persistent OANDA DEMO supervisor process is unavailable."
    }
    Write-Output (
        "OANDA DEMO supervisor: checkpoint {0}; state {1}; heartbeat {2:N1}s; positions/orders {3}/{4}; reconciliation {5}." -f
        $state.checkpoint,
        $state.state,
        $heartbeatAge,
        $observed.positions_count,
        $observed.orders_count,
        $observed.reconciliation
    )
}

Assert-ODINHardwareSafe
Write-Output "[1/5] Validating persistent MT5/OANDA DEMO observation (read-only)."
Assert-ODINAutonomousDemoObservation
if ($ValidateMt5Only) {
    Write-Output "Persistent MT5/OANDA DEMO observation validated. No collection or execution was run."
    exit 0
}

Assert-ODINHardwareSafe
Write-Output "[2/5] Refreshing bounded public ECB observation."
& wsl.exe -d $Distro -u odin -- bash -lc "cd /home/odin/projects/odin && ulimit -n 8192 && timeout 45s python3 -m odin.cli public-data-refresh --timeout-seconds $PublicDataTimeoutSeconds"
if ($LASTEXITCODE -ne 0) { throw "Public observation refresh failed; execution remains blocked." }

Assert-ODINHardwareSafe
Write-Output "[3/5] Persisting one no-decision shadow observation."
& wsl.exe -d $Distro -u odin -- bash -lc "cd /home/odin/projects/odin && ulimit -n 8192 && timeout 45s python3 -m odin.cli shadow-observe"
if ($LASTEXITCODE -ne 0) { throw "Shadow observation failed; execution remains blocked." }

Assert-ODINHardwareSafe
Write-Output "[4/5] Writing factual shadow observation comparison."
& wsl.exe -d $Distro -u odin -- bash -lc "cd /home/odin/projects/odin && ulimit -n 8192 && timeout 45s python3 -m odin.cli shadow-observation-report"
if ($LASTEXITCODE -ne 0) { throw "Shadow comparison report failed; execution remains blocked." }

Assert-ODINHardwareSafe
Write-Output "[5/5] Writing local operational report."
& wsl.exe -d $Distro -u odin -- bash -lc "cd /home/odin/projects/odin && ulimit -n 8192 && timeout 45s python3 -m odin.cli operational-report"
if ($LASTEXITCODE -ne 0) { throw "Operational report failed; execution remains blocked." }

Write-Output "ODIN observations refreshed locally. No decisions, orders, strategies, or execution were run."

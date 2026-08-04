[CmdletBinding()]
param(
    [ValidateRange(5, 30)]
    [int]$Mt5TimeoutSeconds = 10,
    [ValidateRange(5, 60)]
    [int]$PublicDataTimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$Distro = "Ubuntu-ODIN"
$Collector = Join-Path $PSScriptRoot "Read-ODIN-MT5-Demo.ps1"

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

if (-not (Test-Path -LiteralPath $Collector)) {
    throw "The bounded MT5 DEMO collector is unavailable."
}

Assert-ODINHardwareSafe
Write-Output "[1/5] Collecting MT5 DEMO observation (read-only)."
& $Collector -TimeoutSeconds $Mt5TimeoutSeconds
if ($LASTEXITCODE -ne 0) { throw "MT5 DEMO observation failed; no further collection was attempted." }

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

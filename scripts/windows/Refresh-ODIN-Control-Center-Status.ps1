[CmdletBinding()]
param(
    [switch]$HealthOnly,
    [switch]$KillSwitchOnly
)

$ErrorActionPreference = "Stop"
$Distro = "Ubuntu-ODIN"
$RepoLinux = "/home/odin/projects/odin"
$RepoWindows = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin"
$ControlCenter = Join-Path ([Environment]::GetFolderPath("Desktop")) "ODIN - CONTROL CENTER"
$StatusPath = Join-Path $ControlCenter "ODIN - ESTADO ATUAL.txt"
$ConfigPath = Join-Path $RepoWindows "config\demo_execution_rc1.json"
$PreflightPath = Join-Path $RepoWindows "docs\ODIN_DEMO_CANARY_PREFLIGHT.md"
$Stage0Path = "D:\ODIN_LOCAL\reports\demo-execution\stage0-dry-run.json"
$ReportsPath = "D:\ODIN_LOCAL\reports"
$TradeDeskUrl = "http://127.0.0.1:8765/"
$CockpitUrl = "http://127.0.0.1:8765/cockpit"
$ExpectedTerminal = "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe"

function Convert-ToLowerBoolean([object]$Value) {
    if ($Value -eq $true) { return "true" }
    return "false"
}

function Test-LocalEndpoint([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) { return "AVAILABLE" }
        return "UNAVAILABLE (HTTP $($response.StatusCode))"
    }
    catch {
        return "UNAVAILABLE"
    }
}

function Get-LatestReport([string]$Pattern) {
    if (-not (Test-Path -LiteralPath $ReportsPath)) { return "NOT AVAILABLE" }
    $report = Get-ChildItem -LiteralPath $ReportsPath -File -Filter $Pattern -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($null -eq $report) { return "NOT AVAILABLE" }
    return "$($report.FullName) [$($report.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss zzz'))]"
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "ODIN control configuration is unavailable: $ConfigPath"
}
$config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json

$tradeDeskHealth = Test-LocalEndpoint $TradeDeskUrl
$cockpitHealth = Test-LocalEndpoint $CockpitUrl
$expectedTerminalProcesses = @(Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -eq $ExpectedTerminal })
$terminalHealth = if ($expectedTerminalProcesses.Count -eq 1) { "AVAILABLE (PID $($expectedTerminalProcesses[0].ProcessId))" } else { "UNAVAILABLE OR AMBIGUOUS" }
$hermesHealth = if (@(Get-Process -Name "Hermes" -ErrorAction SilentlyContinue).Count -gt 0) { "RUNNING" } else { "NOT RUNNING" }
$ollamaHealth = if (@(Get-Process -Name "ollama" -ErrorAction SilentlyContinue).Count -gt 0) { "RUNNING" } else { "NOT RUNNING" }

if ($KillSwitchOnly) {
    Write-Output "ODIN Kill Switch Status"
    Write-Output "kill_switch_engaged=$(Convert-ToLowerBoolean $config.kill_switch_engaged)"
    Write-Output "safe_to_trade=$(Convert-ToLowerBoolean $config.safe_to_trade)"
    Write-Output "real_trading=$(Convert-ToLowerBoolean $config.real_trading)"
    Write-Output "execution_allowed=$(Convert-ToLowerBoolean $config.execution_allowed)"
    exit 0
}

if ($HealthOnly) {
    Write-Output "ODIN Health Check (read-only)"
    Write-Output "TradeDesk=$tradeDeskHealth"
    Write-Output "Cockpit=$cockpitHealth"
    Write-Output "OANDA_DEMO_MT5=$terminalHealth"
    Write-Output "Hermes=$hermesHealth"
    Write-Output "Ollama=$ollamaHealth"
    Write-Output "safe_to_trade=$(Convert-ToLowerBoolean $config.safe_to_trade)"
    Write-Output "real_trading=$(Convert-ToLowerBoolean $config.real_trading)"
    Write-Output "execution_allowed=$(Convert-ToLowerBoolean $config.execution_allowed)"
    exit 0
}

New-Item -ItemType Directory -Force -Path $ControlCenter | Out-Null
$branch = ((& wsl.exe -d $Distro -u odin --exec git -C $RepoLinux branch --show-current) | Out-String).Trim()
$head = ((& wsl.exe -d $Distro -u odin --exec git -C $RepoLinux rev-parse --short HEAD) | Out-String).Trim()
$worktreeLines = @(& wsl.exe -d $Distro -u odin --exec git -C $RepoLinux status --porcelain)
$worktree = if ($worktreeLines.Count -eq 0) { "CLEAN" } else { "DIRTY" }

$preflightStatus = "NOT AVAILABLE"
if (Test-Path -LiteralPath $PreflightPath) {
    $statusMatch = Select-String -LiteralPath $PreflightPath -Pattern '^Status:\s*\*\*(.+)\*\*' | Select-Object -First 1
    if ($null -ne $statusMatch) { $preflightStatus = $statusMatch.Matches[0].Groups[1].Value }
}

$broker = "NOT AVAILABLE"
$server = "NOT AVAILABLE"
$accountMode = "UNKNOWN"
$stage0Status = "NOT AVAILABLE"
$brokerSubmissionCalled = "NOT AVAILABLE"
if (Test-Path -LiteralPath $Stage0Path) {
    $stage0 = Get-Content -LiteralPath $Stage0Path -Raw | ConvertFrom-Json
    $broker = [string]$stage0.broker
    $server = [string]$stage0.server
    $accountMode = [string]$stage0.account
    $stage0Status = [string]$stage0.status
    $brokerSubmissionCalled = Convert-ToLowerBoolean $stage0.broker_submission_called
}

$lines = @(
    "ODIN - ESTADO ATUAL",
    "generated_at_local=$((Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK'))",
    "generated_at_utc=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))",
    "branch=$branch",
    "HEAD=$head",
    "worktree=$worktree",
    "mode=$($config.mode)",
    "rc1_status=$preflightStatus",
    "safe_to_trade=$(Convert-ToLowerBoolean $config.safe_to_trade)",
    "real_trading=$(Convert-ToLowerBoolean $config.real_trading)",
    "execution_allowed=$(Convert-ToLowerBoolean $config.execution_allowed)",
    "kill_switch_engaged=$(Convert-ToLowerBoolean $config.kill_switch_engaged)",
    "canary_authorized=$(Convert-ToLowerBoolean $config.canary_authorized)",
    "MT5_broker=$broker",
    "MT5_server=$server",
    "MT5_account_mode=$accountMode",
    "MT5_terminal=$terminalHealth",
    "stage0_status=$stage0Status",
    "broker_submission_called=$brokerSubmissionCalled",
    "TradeDesk=$TradeDeskUrl [$tradeDeskHealth]",
    "Cockpit=$CockpitUrl [$cockpitHealth]",
    "reports=$ReportsPath",
    "repository=$RepoWindows",
    "latest_daily_supervisor=$(Get-LatestReport 'odin-daily-supervisor-*.md')",
    "latest_weekly_evolution=$(Get-LatestReport 'odin-weekly-evolution-*.md')"
)
$lines | Set-Content -LiteralPath $StatusPath -Encoding UTF8
Write-Output "ODIN status refreshed: $StatusPath"
Write-Output "safe_to_trade=$(Convert-ToLowerBoolean $config.safe_to_trade); real_trading=$(Convert-ToLowerBoolean $config.real_trading); execution_allowed=$(Convert-ToLowerBoolean $config.execution_allowed)"

[CmdletBinding()]
param(
    [string]$TerminalPath = "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe",
    [string]$PythonPath = "D:\ODIN_LOCAL\runtime\mt5_probe_venv\Scripts\python.exe",
    [string]$RepoRoot = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin",
    [ValidateRange(5, 300)]
    [int]$CycleSeconds = 30
)

$ErrorActionPreference = "Stop"
$StartupTrace = "D:\ODIN_LOCAL\state\autonomous_demo_startup.log"
function Write-StartupTrace([string]$Step) {
    $line = "{0} {1}" -f [DateTime]::UtcNow.ToString("o"), $Step
    Add-Content -LiteralPath $StartupTrace -Value $line -Encoding utf8
}
Write-StartupTrace "LAUNCHER_STARTED"
$ExpectedTerminal = "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe"
$ExcludedTerminal = "D:\ODIN_LOCAL\mt5\terminal64.exe"
$StateRoot = "D:\ODIN_LOCAL\state"
$LogRoot = "D:\ODIN_LOCAL\logs\autonomous-demo"
$ReportRoot = "D:\ODIN_LOCAL\reports"
$envFile = Join-Path $RepoRoot ".env"
$probe = Join-Path $RepoRoot "scripts\windows\mt5_autonomous_demo_supervisor.py"
$dashboardLauncher = "D:\ODIN_LOCAL\runtime\Start-ODIN-Dashboard-Persistent.ps1"
$config = Join-Path $RepoRoot "config\demo_execution_rc2.json"

if ($TerminalPath -ine $ExpectedTerminal -or $TerminalPath -ieq $ExcludedTerminal) {
    throw "ODIN RC2 terminal path is not allowlisted."
}
Write-StartupTrace "TERMINAL_ALLOWLIST_OK"
foreach ($requiredPath in @($TerminalPath, $PythonPath, $envFile, $probe, $dashboardLauncher, $config)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "ODIN RC2 prerequisite unavailable."
    }
}
Write-StartupTrace "REQUIRED_PATHS_OK"

$values = @{}
Get-Content -LiteralPath $envFile | ForEach-Object {
    if ($_ -match '^[^#=]+=.') {
        $parts = $_.Split('=', 2)
        $values[$parts[0].Trim()] = $parts[1].Trim()
    }
}
foreach ($key in @('ODIN_OANDA_ACCOUNT_MODE', 'ODIN_OANDA_LOGIN', 'ODIN_OANDA_SERVER')) {
    if ([string]::IsNullOrWhiteSpace($values[$key])) {
        throw "OANDA DEMO identity configuration is incomplete."
    }
}
if ($values['ODIN_OANDA_ACCOUNT_MODE'].ToLowerInvariant() -notin @('demo', 'practice')) {
    throw "OANDA account mode is not deterministically DEMO."
}
if ($values['ODIN_OANDA_SERVER'] -ne 'OANDATMS-MT5') {
    throw "OANDA server is not allowlisted."
}
if ($values['ODIN_OANDA_LOGIN'] -notmatch '^\d+$') {
    throw "OANDA DEMO login identifier is invalid."
}
Write-StartupTrace "IDENTITY_CONFIG_OK"

New-Item -ItemType Directory -Force -Path $StateRoot, $LogRoot, $ReportRoot | Out-Null
Write-StartupTrace "DIRECTORIES_READY"
& $dashboardLauncher
Write-StartupTrace "DASHBOARD_READY"

$env:ODIN_RC2_EXPECTED_LOGIN = $values['ODIN_OANDA_LOGIN']
$env:ODIN_RC2_TERMINAL_PATH = $TerminalPath
$env:ODIN_RC2_REPO_SRC = Join-Path $RepoRoot "src"
$env:ODIN_RC2_WINDOWS_SCRIPTS = Join-Path $RepoRoot "scripts\windows"
$env:ODIN_RC2_CONFIG_PATH = $config
$env:ODIN_RC2_LEDGER_PATH = "D:\ODIN_LOCAL\runtime\demo_execution_ledger.jsonl"
$env:ODIN_RC2_DECISION_LEDGER_PATH = "D:\ODIN_LOCAL\runtime\demo_decision_ledger.jsonl"
$env:ODIN_RC2_MT5_STATE_PATH = "D:\ODIN_LOCAL\runtime\mt5_demo_readonly.json"
$env:ODIN_RC2_STATE_PATH = Join-Path $StateRoot "autonomous_demo_state.json"
$env:ODIN_RC2_HEARTBEAT_PATH = Join-Path $StateRoot "autonomous_demo_heartbeat.json"
$env:ODIN_RC2_CONTROL_PATH = Join-Path $StateRoot "autonomous_demo_control.json"
$env:ODIN_RC2_INCIDENTS_PATH = Join-Path $StateRoot "autonomous_demo_incidents.jsonl"
$env:ODIN_RC2_REPORT_ROOT = $ReportRoot
$env:ODIN_RC2_HERMES_CLAIMS_PATH = "D:\ODIN_LOCAL\runtime\hermes_claims.jsonl"
$env:ODIN_RC2_DASHBOARD_LAUNCHER = $dashboardLauncher
$env:ODIN_RC2_CYCLE_SECONDS = [string]$CycleSeconds
$env:ODIN_RC2_BRANCH = "feature/autonomous-demo-operations-rc2"
$checkpoint = (& wsl.exe -d Ubuntu-ODIN --user odin --exec git -C /home/odin/projects/odin rev-parse --short HEAD)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($checkpoint)) {
    throw "ODIN RC2 checkpoint lookup failed."
}
$env:ODIN_RC2_CHECKPOINT = $checkpoint.Trim()
Write-StartupTrace "SUPERVISOR_ENV_READY"

try {
    $stdout = Join-Path $LogRoot "supervisor.stdout.log"
    $stderr = Join-Path $LogRoot "supervisor.stderr.log"
    Write-StartupTrace "SUPERVISOR_STARTING"
    $supervisor = Start-Process -FilePath $PythonPath `
        -ArgumentList @($probe) `
        -WindowStyle Hidden `
        -PassThru `
        -Wait `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr
    exit $supervisor.ExitCode
}
finally {
    @(
        'ODIN_RC2_EXPECTED_LOGIN', 'ODIN_RC2_TERMINAL_PATH', 'ODIN_RC2_REPO_SRC',
        'ODIN_RC2_WINDOWS_SCRIPTS', 'ODIN_RC2_CONFIG_PATH', 'ODIN_RC2_LEDGER_PATH',
        'ODIN_RC2_DECISION_LEDGER_PATH',
        'ODIN_RC2_MT5_STATE_PATH', 'ODIN_RC2_STATE_PATH', 'ODIN_RC2_HEARTBEAT_PATH',
        'ODIN_RC2_CONTROL_PATH', 'ODIN_RC2_INCIDENTS_PATH',
        'ODIN_RC2_REPORT_ROOT', 'ODIN_RC2_HERMES_CLAIMS_PATH',
        'ODIN_RC2_DASHBOARD_LAUNCHER', 'ODIN_RC2_CYCLE_SECONDS',
        'ODIN_RC2_BRANCH', 'ODIN_RC2_CHECKPOINT'
    ) | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
}

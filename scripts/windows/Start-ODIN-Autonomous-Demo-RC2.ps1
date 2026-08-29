[CmdletBinding()]
param(
    [string]$TerminalPath = "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe",
    [string]$PythonPath = "D:\ODIN_LOCAL\runtime\mt5_probe_venv\Scripts\python.exe",
    [string]$RepoRoot = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin",
    [ValidateRange(5, 300)]
    [int]$CycleSeconds = 30
)

$ErrorActionPreference = "Stop"
$ExpectedTerminal = "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe"
$ExcludedTerminal = "D:\ODIN_LOCAL\mt5\terminal64.exe"
$StateRoot = "D:\ODIN_LOCAL\state"
$LogRoot = "D:\ODIN_LOCAL\logs\autonomous-demo"
$ReportRoot = "D:\ODIN_LOCAL\reports"
$envFile = Join-Path $RepoRoot ".env"
$probe = Join-Path $RepoRoot "scripts\windows\mt5_autonomous_demo_supervisor.py"
$dashboardLauncher = Join-Path $RepoRoot "scripts\windows\Start-ODIN-Dashboard-Persistent.ps1"
$config = Join-Path $RepoRoot "config\demo_execution_rc2.json"

if ($TerminalPath -ine $ExpectedTerminal -or $TerminalPath -ieq $ExcludedTerminal) {
    throw "ODIN RC2 terminal path is not allowlisted."
}
foreach ($requiredPath in @($TerminalPath, $PythonPath, $envFile, $probe, $dashboardLauncher, $config)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "ODIN RC2 prerequisite unavailable."
    }
}

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

New-Item -ItemType Directory -Force -Path $StateRoot, $LogRoot, $ReportRoot | Out-Null
& $dashboardLauncher

$env:ODIN_RC2_EXPECTED_LOGIN = $values['ODIN_OANDA_LOGIN']
$env:ODIN_RC2_TERMINAL_PATH = $TerminalPath
$env:ODIN_RC2_REPO_SRC = Join-Path $RepoRoot "src"
$env:ODIN_RC2_WINDOWS_SCRIPTS = Join-Path $RepoRoot "scripts\windows"
$env:ODIN_RC2_CONFIG_PATH = $config
$env:ODIN_RC2_LEDGER_PATH = "D:\ODIN_LOCAL\runtime\demo_execution_ledger.jsonl"
$env:ODIN_RC2_MT5_STATE_PATH = "D:\ODIN_LOCAL\runtime\mt5_demo_readonly.json"
$env:ODIN_RC2_STATE_PATH = Join-Path $StateRoot "autonomous_demo_state.json"
$env:ODIN_RC2_HEARTBEAT_PATH = Join-Path $StateRoot "autonomous_demo_heartbeat.json"
$env:ODIN_RC2_CONTROL_PATH = Join-Path $StateRoot "autonomous_demo_control.json"
$env:ODIN_RC2_INCIDENTS_PATH = Join-Path $StateRoot "autonomous_demo_incidents.jsonl"
$env:ODIN_RC2_DASHBOARD_LAUNCHER = $dashboardLauncher
$env:ODIN_RC2_CYCLE_SECONDS = [string]$CycleSeconds
$env:ODIN_RC2_BRANCH = "feature/autonomous-demo-operations-rc2"
$env:ODIN_RC2_CHECKPOINT = (& git -C $RepoRoot rev-parse --short HEAD 2>$null)

try {
    $stdout = Join-Path $LogRoot "supervisor.stdout.log"
    $stderr = Join-Path $LogRoot "supervisor.stderr.log"
    & $PythonPath $probe 1>> $stdout 2>> $stderr
    exit $LASTEXITCODE
}
finally {
    @(
        'ODIN_RC2_EXPECTED_LOGIN', 'ODIN_RC2_TERMINAL_PATH', 'ODIN_RC2_REPO_SRC',
        'ODIN_RC2_WINDOWS_SCRIPTS', 'ODIN_RC2_CONFIG_PATH', 'ODIN_RC2_LEDGER_PATH',
        'ODIN_RC2_MT5_STATE_PATH', 'ODIN_RC2_STATE_PATH', 'ODIN_RC2_HEARTBEAT_PATH',
        'ODIN_RC2_CONTROL_PATH', 'ODIN_RC2_INCIDENTS_PATH',
        'ODIN_RC2_DASHBOARD_LAUNCHER', 'ODIN_RC2_CYCLE_SECONDS',
        'ODIN_RC2_BRANCH', 'ODIN_RC2_CHECKPOINT'
    ) | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }
}

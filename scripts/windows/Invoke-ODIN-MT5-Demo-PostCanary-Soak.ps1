[CmdletBinding()]
param(
    [ValidateRange(1, 360)]
    [int]$MaxCycles = 360,
    [ValidateRange(30, 300)]
    [int]$IntervalSeconds = 60,
    [string]$TerminalPath = "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe",
    [string]$PythonPath = "D:\ODIN_LOCAL\runtime\mt5_probe_venv\Scripts\python.exe",
    [string]$RepoRoot = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin",
    [string]$LedgerPath = "D:\ODIN_LOCAL\runtime\demo_execution_ledger.jsonl",
    [string]$ReportDir = "D:\ODIN_LOCAL\reports",
    [string]$CanaryReportPath = "D:\ODIN_LOCAL\reports\demo-execution\canary-one-shot.json",
    [string]$CanaryMarkerPath = "D:\ODIN_LOCAL\runtime\.demo_canary_attempted.json"
)

# Bounded observation only. This launcher cannot submit, modify or close a trade.
$ErrorActionPreference = "Stop"
$envFile = Join-Path $RepoRoot ".env"
$probe = Join-Path $RepoRoot "scripts\windows\mt5_demo_post_canary_soak.py"
$control = Join-Path $RepoRoot "config\demo_execution_rc1.json"
foreach ($requiredPath in @(
    $TerminalPath, $PythonPath, $envFile, $probe, $control,
    $LedgerPath, $CanaryReportPath, $CanaryMarkerPath
)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "ODIN DEMO post-CANARY soak prerequisite unavailable."
    }
}

$running = @(Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -eq $TerminalPath })
if ($running.Count -ne 1) {
    throw "Exactly one expected OANDA TMS terminal must already be running."
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

$checkpoint = (& wsl.exe -d Ubuntu-ODIN --user odin --exec git -C /home/odin/projects/odin rev-parse --short HEAD).Trim()
$env:ODIN_RC1_EXPECTED_LOGIN = $values['ODIN_OANDA_LOGIN']
$env:ODIN_RC1_EXPECTED_SERVER = $values['ODIN_OANDA_SERVER']
$env:ODIN_RC1_TERMINAL_PATH = $TerminalPath
$env:ODIN_RC1_REPO_SRC = Join-Path $RepoRoot "src"
$env:ODIN_RC1_CONTROL_PATH = $control
$env:ODIN_RC1_LEDGER_PATH = $LedgerPath
$env:ODIN_RC1_SOAK_REPORT_DIR = $ReportDir
$env:ODIN_RC1_GIT_CHECKPOINT = $checkpoint
$env:ODIN_RC1_CANARY_REPORT_PATH = $CanaryReportPath
$env:ODIN_RC1_CANARY_MARKER_PATH = $CanaryMarkerPath
$env:ODIN_RC1_SOAK_MAX_CYCLES = [string]$MaxCycles
$env:ODIN_RC1_SOAK_INTERVAL_SECONDS = [string]$IntervalSeconds
try {
    & $PythonPath $probe
    exit $LASTEXITCODE
}
finally {
    Remove-Item Env:ODIN_RC1_EXPECTED_LOGIN,Env:ODIN_RC1_EXPECTED_SERVER,Env:ODIN_RC1_TERMINAL_PATH,Env:ODIN_RC1_REPO_SRC,Env:ODIN_RC1_CONTROL_PATH,Env:ODIN_RC1_LEDGER_PATH,Env:ODIN_RC1_SOAK_REPORT_DIR,Env:ODIN_RC1_GIT_CHECKPOINT,Env:ODIN_RC1_CANARY_REPORT_PATH,Env:ODIN_RC1_CANARY_MARKER_PATH,Env:ODIN_RC1_SOAK_MAX_CYCLES,Env:ODIN_RC1_SOAK_INTERVAL_SECONDS -ErrorAction SilentlyContinue
}

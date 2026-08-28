[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [switch]$ConfirmOneShot,
    [string]$TerminalPath = "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe",
    [string]$PythonPath = "D:\ODIN_LOCAL\runtime\mt5_probe_venv\Scripts\python.exe",
    [string]$RepoRoot = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin",
    [string]$LedgerPath = "D:\ODIN_LOCAL\runtime\demo_execution_ledger.jsonl",
    [string]$ReportPath = "D:\ODIN_LOCAL\reports\demo-execution\canary-one-shot.json"
)

# One human-confirmed DEMO CANARY only. There are no retry or batch paths here.
$ErrorActionPreference = "Stop"
if (-not $ConfirmOneShot) {
    throw "Explicit one-shot human confirmation is required."
}

$envFile = Join-Path $RepoRoot ".env"
$probe = Join-Path $RepoRoot "scripts\windows\mt5_demo_canary_one_shot.py"
$control = Join-Path $RepoRoot "config\demo_execution_rc1.json"
$attemptMarker = Join-Path (Split-Path -Parent $LedgerPath) ".demo_canary_attempted.json"
foreach ($requiredPath in @($TerminalPath, $PythonPath, $envFile, $probe, $control)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "ODIN DEMO CANARY prerequisite unavailable."
    }
}
if (Test-Path -LiteralPath $attemptMarker) {
    throw "The one-shot DEMO CANARY was already attempted."
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
if ($values['ODIN_OANDA_LOGIN'] -notmatch '^\d+$') {
    throw "OANDA DEMO login identifier is invalid."
}

$env:ODIN_RC1_HUMAN_CONFIRMATION = "CONFIRM_ONE_DEMO_CANARY"
$env:ODIN_RC1_EXPECTED_LOGIN = $values['ODIN_OANDA_LOGIN']
$env:ODIN_RC1_EXPECTED_SERVER = $values['ODIN_OANDA_SERVER']
$env:ODIN_RC1_TERMINAL_PATH = $TerminalPath
$env:ODIN_RC1_REPO_SRC = Join-Path $RepoRoot "src"
$env:ODIN_RC1_CONTROL_PATH = $control
$env:ODIN_RC1_LEDGER_PATH = $LedgerPath
$env:ODIN_RC1_REPORT_PATH = $ReportPath
try {
    & $PythonPath $probe
    exit $LASTEXITCODE
}
finally {
    Remove-Item Env:ODIN_RC1_HUMAN_CONFIRMATION,Env:ODIN_RC1_EXPECTED_LOGIN,Env:ODIN_RC1_EXPECTED_SERVER,Env:ODIN_RC1_TERMINAL_PATH,Env:ODIN_RC1_REPO_SRC,Env:ODIN_RC1_CONTROL_PATH,Env:ODIN_RC1_LEDGER_PATH,Env:ODIN_RC1_REPORT_PATH -ErrorAction SilentlyContinue
}

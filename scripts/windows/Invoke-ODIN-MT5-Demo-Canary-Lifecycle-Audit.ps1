[CmdletBinding()]
param(
    [string]$TerminalPath = "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe",
    [string]$PythonPath = "D:\ODIN_LOCAL\runtime\mt5_probe_venv\Scripts\python.exe",
    [string]$RepoRoot = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin",
    [string]$ExecutionLedgerPath = "D:\ODIN_LOCAL\runtime\demo_execution_ledger.jsonl",
    [string]$DecisionLedgerPath = "D:\ODIN_LOCAL\runtime\demo_decision_ledger.jsonl",
    [string]$CanaryReportPath = "D:\ODIN_LOCAL\reports\demo-execution\canary-one-shot.json",
    [string]$AuditReportPath = "D:\ODIN_LOCAL\reports\demo-execution\canary-lifecycle-audit.json"
)

# Read broker history and append only audit/closure records. No broker action exists here.
$ErrorActionPreference = "Stop"
$envFile = Join-Path $RepoRoot ".env"
$probe = Join-Path $RepoRoot "scripts\windows\mt5_demo_canary_lifecycle_audit.py"
foreach ($requiredPath in @(
    $TerminalPath, $PythonPath, $envFile, $probe, $ExecutionLedgerPath, $CanaryReportPath
)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "ODIN DEMO CANARY lifecycle audit prerequisite unavailable."
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
if ($values['ODIN_OANDA_LOGIN'] -notmatch '^\d+$') {
    throw "OANDA DEMO login identifier is invalid."
}

$env:ODIN_RC1_EXPECTED_LOGIN = $values['ODIN_OANDA_LOGIN']
$env:ODIN_RC1_EXPECTED_SERVER = $values['ODIN_OANDA_SERVER']
$env:ODIN_RC1_TERMINAL_PATH = $TerminalPath
$env:ODIN_RC1_REPO_SRC = Join-Path $RepoRoot "src"
$env:ODIN_RC1_LEDGER_PATH = $ExecutionLedgerPath
$env:ODIN_RC1_DECISION_LEDGER_PATH = $DecisionLedgerPath
$env:ODIN_RC1_CANARY_REPORT_PATH = $CanaryReportPath
$env:ODIN_RC1_AUDIT_REPORT_PATH = $AuditReportPath
try {
    & $PythonPath $probe
    exit $LASTEXITCODE
}
finally {
    Remove-Item Env:ODIN_RC1_EXPECTED_LOGIN,Env:ODIN_RC1_EXPECTED_SERVER,Env:ODIN_RC1_TERMINAL_PATH,Env:ODIN_RC1_REPO_SRC,Env:ODIN_RC1_LEDGER_PATH,Env:ODIN_RC1_DECISION_LEDGER_PATH,Env:ODIN_RC1_CANARY_REPORT_PATH,Env:ODIN_RC1_AUDIT_REPORT_PATH -ErrorAction SilentlyContinue
}

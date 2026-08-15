[CmdletBinding()]
param(
    [string]$TerminalPath = "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe",
    [string]$PythonPath = "D:\ODIN_LOCAL\runtime\mt5_probe_venv\Scripts\python.exe",
    [string]$ArtifactRoot = "D:\ODIN_LOCAL",
    [datetime]$StartUtc = [datetime]"2026-07-01T00:00:00Z",
    [datetime]$EndUtc = [datetime]"2026-08-01T00:00:00Z"
)

# P0 importer: observation only.  It loads no configuration file or credentials.
# Permitted MT5 calls are initialize, terminal_info, account_info, symbol_info,
# copy_rates_range, copy_ticks_range and shutdown.  No trade operation exists here.
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $PythonPath)) { throw "MT5 Python runtime unavailable." }
if (-not (Test-Path -LiteralPath $TerminalPath)) { throw "MT5 terminal executable unavailable." }
if ($StartUtc.Kind -ne [DateTimeKind]::Utc) { $StartUtc = $StartUtc.ToUniversalTime() }
if ($EndUtc.Kind -ne [DateTimeKind]::Utc) { $EndUtc = $EndUtc.ToUniversalTime() }
if ($StartUtc -ge $EndUtc) { throw "UTC interval is invalid." }
$running = @(Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.ExecutablePath -eq $TerminalPath })
if ($running.Count -ne 1) { throw "Exactly one requested OANDA TMS terminal must already be running." }

$env:ODIN_P0_TERMINAL = $TerminalPath; $env:ODIN_P0_ROOT = $ArtifactRoot
$env:ODIN_P0_START = $StartUtc.ToString("yyyy-MM-ddTHH:mm:ssZ"); $env:ODIN_P0_END = $EndUtc.ToString("yyyy-MM-ddTHH:mm:ssZ")
$temporary = Join-Path $env:TEMP "odin_mt5_oanda_p0_import.py"
@'
import json, os, sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, r"\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin\src")
import MetaTrader5 as mt5
from odin.data.mt5_oanda_history import Mt5OandaHistoryError, import_mt5_oanda_tms_m1

def utc(s): return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
def safe_failure(reason, **extra):
    print(json.dumps({"status":"BLOCKED","reason":reason,**extra,"safe_to_trade":False,"real_trading":False,"execution_allowed":False}, sort_keys=True))

path=os.environ["ODIN_P0_TERMINAL"]; start=utc(os.environ["ODIN_P0_START"]); end=utc(os.environ["ODIN_P0_END"])
if not mt5.initialize(path):
    code, description=mt5.last_error(); safe_failure("initialize_failed", last_error_code=code, last_error_description=description); raise SystemExit(1)
try:
    terminal=mt5.terminal_info(); account=mt5.account_info(); symbol=mt5.symbol_info("EURUSD")
    if account is None or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO: safe_failure("demo_not_verified"); raise SystemExit(1)
    if account.company != "OANDA TMS Brokers S.A." or account.server != "OANDATMS-MT5": safe_failure("unexpected_provider_or_server"); raise SystemExit(1)
    if symbol is None or not symbol.visible: safe_failure("eurusd_unavailable"); raise SystemExit(1)
    records=mt5.copy_rates_range("EURUSD", mt5.TIMEFRAME_M1, start, end)
    if records is None or not len(records): safe_failure("m1_history_unavailable"); raise SystemExit(1)
    rates=[{name:(item[name].item() if hasattr(item[name], "item") else item[name]) for name in records.dtype.names} for item in records]
    ticks={}
    for before, after in zip(rates, rates[1:]):
        left=(int(before["time"])+60)*1000; right=int(after["time"])*1000
        if right <= left: continue
        query=mt5.copy_ticks_range("EURUSD", datetime.fromtimestamp(left/1000, timezone.utc), datetime.fromtimestamp(right/1000, timezone.utc)-timedelta(milliseconds=1), mt5.COPY_TICKS_ALL)
        ticks[(left,right)]=0 if query is None else len(query)
    result=import_mt5_oanda_tms_m1(rates=rates,start_utc=start,end_utc=end,acquired_at=datetime.now(timezone.utc),artifact_root=os.environ["ODIN_P0_ROOT"],tick_counts=ticks,terminal_version=str(getattr(terminal,"build",None)),runtime_version=getattr(mt5,"__version__",None))
    public=("status","reason","dataset_hash","raw_m1_sha256","raw_m1_bars","artifact_path","manifest_path","safe_to_trade","real_trading","execution_allowed")
    print(json.dumps({key:result[key] for key in public if key in result},sort_keys=True))
except Mt5OandaHistoryError as error:
    safe_failure(str(error)); raise SystemExit(1)
finally:
    mt5.shutdown()
'@ | Set-Content -LiteralPath $temporary -Encoding utf8
try { & $PythonPath $temporary; exit $LASTEXITCODE }
finally { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue; Remove-Item Env:ODIN_P0_TERMINAL,Env:ODIN_P0_ROOT,Env:ODIN_P0_START,Env:ODIN_P0_END -ErrorAction SilentlyContinue }

[CmdletBinding()]
param(
    [ValidateRange(5, 30)]
    [int]$TimeoutSeconds = 10
)

$ErrorActionPreference = "Stop"
$envFile = "\\wsl.localhost\Ubuntu-ODIN\home\odin\projects\odin\.env"
$python = "D:\ODIN_LOCAL\runtime\mt5_probe_venv\Scripts\python.exe"
$output = "D:\ODIN_LOCAL\runtime\mt5_demo_readonly.json"
if (-not (Test-Path -LiteralPath $envFile) -or -not (Test-Path -LiteralPath $python)) { throw "MT5 DEMO read-only prerequisites are unavailable." }

$values = @{}
Get-Content -LiteralPath $envFile | ForEach-Object {
    if ($_ -match '^[^#=]+=.') { $parts = $_.Split('=', 2); $values[$parts[0].Trim()] = $parts[1].Trim() }
}
foreach ($key in @('ODIN_MT5_ACCOUNT_MODE','ODIN_MT5_LOGIN','ODIN_MT5_PASSWORD','ODIN_MT5_SERVER')) {
    if ([string]::IsNullOrWhiteSpace($values[$key])) { throw "MT5 DEMO configuration is incomplete." }
}
if ($values['ODIN_MT5_ACCOUNT_MODE'].ToLowerInvariant() -ne 'demo' -or $values['ODIN_MT5_LOGIN'] -notmatch '^\d+$') { throw "MT5 DEMO configuration is blocked." }

$env:ODIN_MT5_LOGIN = $values['ODIN_MT5_LOGIN']; $env:ODIN_MT5_PASSWORD = $values['ODIN_MT5_PASSWORD']; $env:ODIN_MT5_SERVER = $values['ODIN_MT5_SERVER']
$scriptPath = Join-Path $env:TEMP "odin_mt5_readonly_probe.py"
@'
import hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
import MetaTrader5 as mt5

out = Path(r"D:\ODIN_LOCAL\runtime\mt5_demo_readonly.json")
audit = Path(r"D:\ODIN_LOCAL\logs\mt5_demo_readonly.jsonl")
ok = mt5.initialize(path=r"D:\ODIN_LOCAL\mt5\terminal64.exe", login=int(os.environ["ODIN_MT5_LOGIN"]), password=os.environ["ODIN_MT5_PASSWORD"], server=os.environ["ODIN_MT5_SERVER"], timeout=10000)
try:
    if not ok:
        code, _ = mt5.last_error(); result={"status":"BLOCKED","reason":"connection_failed","error_code":code}
    else:
        account=mt5.account_info(); is_demo=bool(account and account.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO)
        positions=mt5.positions_get() or ()
        tick=mt5.symbol_info_tick("EURUSD") if is_demo else None
        rates=mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_M15, 0, 32) if is_demo else None
        market={"symbol":"EURUSD","status":"OK" if tick else "UNAVAILABLE","bid":float(tick.bid) if tick else None,"ask":float(tick.ask) if tick else None,"as_of":datetime.fromtimestamp(tick.time, timezone.utc).isoformat(timespec="seconds") if tick else None,"candles":[{"time":datetime.fromtimestamp(int(row["time"]), timezone.utc).isoformat(timespec="seconds"),"open":float(row["open"]),"high":float(row["high"]),"low":float(row["low"]),"close":float(row["close"])} for row in (rates if rates is not None else ())]}
        result={"status":"CONNECTED_DEMO_READ_ONLY" if is_demo else "BLOCKED","reason":"demo_verified" if is_demo else "account_mode_not_demo","as_of":datetime.now(timezone.utc).isoformat(timespec="seconds"),"account":{"currency":account.currency,"balance":account.balance,"equity":account.equity,"margin":account.margin,"free_margin":account.margin_free} if is_demo else {},"positions":[{"symbol":p.symbol,"volume":p.volume,"profit":p.profit,"type":"BUY" if p.type==0 else "SELL"} for p in positions] if is_demo else [],"market":market if is_demo else {}}
    result.update({"terminal_connected":bool(ok),"execution_allowed":False,"safe_to_trade":False,"real_trading":False})
    canonical=json.dumps(result, sort_keys=True, separators=(",",":"))
    result["content_hash"]=hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    tmp=out.with_suffix(".tmp"); tmp.write_text(json.dumps(result, sort_keys=True), encoding="utf-8"); tmp.replace(out)
    audit.parent.mkdir(parents=True, exist_ok=True)
    event={"event":"mt5_demo_readonly_snapshot","as_of":result.get("as_of"),"status":result.get("status"),"market":{"symbol":result.get("market",{}).get("symbol"),"as_of":result.get("market",{}).get("as_of"),"status":result.get("market",{}).get("status"),"candles":len(result.get("market",{}).get("candles",[]))},"positions_count":len(result.get("positions",[])),"content_hash":result["content_hash"],"execution_allowed":False}
    with audit.open("a", encoding="utf-8") as handle: handle.write(json.dumps(event, sort_keys=True)+"\n")
    print(json.dumps({"status":result["status"],"positions_count":len(result.get("positions",[])),"execution_allowed":False,"content_hash":result["content_hash"]}))
    sys.exit(0 if result["status"]=="CONNECTED_DEMO_READ_ONLY" else 1)
finally: mt5.shutdown()
'@ | Set-Content -LiteralPath $scriptPath -Encoding utf8
try { & $python $scriptPath; exit $LASTEXITCODE } finally { Remove-Item -LiteralPath $scriptPath -Force -ErrorAction SilentlyContinue; Remove-Item Env:ODIN_MT5_LOGIN,Env:ODIN_MT5_PASSWORD,Env:ODIN_MT5_SERVER -ErrorAction SilentlyContinue }

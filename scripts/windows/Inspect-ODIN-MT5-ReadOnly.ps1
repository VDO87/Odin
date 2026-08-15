[CmdletBinding()]
param(
    [string]$TerminalPath = "C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe",
    [string]$Symbol = "EURUSD",
    [datetime]$StartUtc = [datetime]"2026-07-01T00:00:00Z",
    [datetime]$EndUtc = [datetime]"2026-08-01T00:00:00Z",
    [string]$PythonPath = "D:\ODIN_LOCAL\runtime\mt5_probe_venv\Scripts\python.exe"
)

# This script is intentionally observation-only.  It never loads .env or passes
# account credentials to MetaTrader5.  It also refuses to make initialize() launch
# a terminal: the exact requested terminal must already be running.
$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $PythonPath)) { throw "MT5 Python runtime unavailable." }
if (-not (Test-Path -LiteralPath $TerminalPath)) { throw "MT5 terminal executable unavailable." }
if ($StartUtc.Kind -ne [DateTimeKind]::Utc) { $StartUtc = $StartUtc.ToUniversalTime() }
if ($EndUtc.Kind -ne [DateTimeKind]::Utc) { $EndUtc = $EndUtc.ToUniversalTime() }
if ($StartUtc -ge $EndUtc) { throw "UTC interval is invalid." }

$running = @(Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -eq $TerminalPath })
if ($running.Count -ne 1) {
    [pscustomobject]@{
        status = "BLOCKED"; reason = "exact_terminal_not_running"; terminal_path = $TerminalPath
        matching_terminal_processes = $running.Count; safe_to_trade = $false; real_trading = $false; execution_allowed = $false
    } | ConvertTo-Json -Compress
    exit 1
}

$env:ODIN_MT5_RO_TERMINAL_PATH = $TerminalPath
$env:ODIN_MT5_RO_SYMBOL = $Symbol
$env:ODIN_MT5_RO_START_UTC = $StartUtc.ToString("yyyy-MM-ddTHH:mm:ssZ")
$env:ODIN_MT5_RO_END_UTC = $EndUtc.ToString("yyyy-MM-ddTHH:mm:ssZ")
$temporary = Join-Path $env:TEMP "odin_mt5_readonly_inspect.py"
@'
import json
import os
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def stamp(seconds: int) -> str:
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    path = os.environ["ODIN_MT5_RO_TERMINAL_PATH"]
    symbol_name = os.environ["ODIN_MT5_RO_SYMBOL"]
    start = utc(os.environ["ODIN_MT5_RO_START_UTC"])
    end = utc(os.environ["ODIN_MT5_RO_END_UTC"])
    connected = mt5.initialize(path)
    try:
        if not connected:
            code, description = mt5.last_error()
            print(json.dumps({"status": "BLOCKED", "reason": "initialize_failed", "last_error_code": code, "last_error_description": description, "safe_to_trade": False, "real_trading": False, "execution_allowed": False}, sort_keys=True))
            return
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if account is None or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            print(json.dumps({"status": "BLOCKED", "reason": "demo_not_verified", "terminal_connected": bool(getattr(terminal, "connected", False)), "safe_to_trade": False, "real_trading": False, "execution_allowed": False}, sort_keys=True))
            return
        symbol = mt5.symbol_info(symbol_name)
        if symbol is None or not symbol.visible:
            print(json.dumps({"status": "BLOCKED", "reason": "symbol_unavailable", "symbol": symbol_name, "safe_to_trade": False, "real_trading": False, "execution_allowed": False}, sort_keys=True))
            return
        m1 = mt5.copy_rates_range(symbol_name, mt5.TIMEFRAME_M1, start, end)
        if m1 is None or not len(m1):
            print(json.dumps({"status": "BLOCKED", "reason": "m1_history_unavailable", "symbol": symbol_name, "safe_to_trade": False, "real_trading": False, "execution_allowed": False}, sort_keys=True))
            return
        timestamps = [int(row["time"]) for row in m1]
        gaps = []
        for previous, current in zip(timestamps, timestamps[1:]):
            duration = current - previous
            if duration == 60:
                continue
            before = datetime.fromtimestamp(previous, timezone.utc)
            after = datetime.fromtimestamp(current, timezone.utc)
            ticks = mt5.copy_ticks_range(symbol_name, before + timedelta(minutes=1), after - timedelta(milliseconds=1), mt5.COPY_TICKS_ALL)
            tick_count = 0 if ticks is None else len(ticks)
            if duration > 86_400 and before.weekday() == 4:
                classification, rule = "EXPECTED_GAP", "weekend_market_closed"
            elif tick_count == 0:
                classification, rule = "NO_TICK_GAP", "no_ticks_in_missing_M1_minutes"
            else:
                classification, rule = "SUSPICIOUS_GAP", "ticks_present_in_missing_M1_minutes"
            gaps.append({"from_utc": stamp(previous), "to_utc": stamp(current), "duration_seconds": duration, "missing_m1_minutes": duration // 60 - 1, "tick_count_in_missing_minutes": tick_count, "classification": classification, "rule": rule})
        counts = {name: sum(gap["classification"] == name for gap in gaps) for name in ("EXPECTED_GAP", "NO_TICK_GAP", "SUSPICIOUS_GAP")}
        print(json.dumps({"status": "OBSERVED", "read_only": True, "broker_company": account.company, "server": account.server, "terminal_path": terminal.path, "terminal_connected": bool(terminal.connected), "symbol": symbol_name, "timeframe": "M1", "period_start_utc": start.isoformat().replace("+00:00", "Z"), "period_end_utc": end.isoformat().replace("+00:00", "Z"), "first_bar_utc": stamp(timestamps[0]), "last_bar_utc": stamp(timestamps[-1]), "bars": len(m1), "gap_counts": counts, "gaps": gaps, "safe_to_trade": False, "real_trading": False, "execution_allowed": False}, sort_keys=True))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
'@ | Set-Content -LiteralPath $temporary -Encoding utf8
try { & $PythonPath $temporary; exit $LASTEXITCODE }
finally {
    Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    Remove-Item Env:ODIN_MT5_RO_TERMINAL_PATH,Env:ODIN_MT5_RO_SYMBOL,Env:ODIN_MT5_RO_START_UTC,Env:ODIN_MT5_RO_END_UTC -ErrorAction SilentlyContinue
}

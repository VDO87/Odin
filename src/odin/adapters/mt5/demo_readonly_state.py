"""Read the sanitized MT5 DEMO collector state without terminal contact."""
from __future__ import annotations
import json
from pathlib import Path

def read_demo_readonly_state(path: str = "/mnt/d/ODIN_LOCAL/runtime/mt5_demo_readonly.json") -> dict[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _blocked("demo_readonly_state_missing")
    if not isinstance(value, dict) or value.get("status") != "CONNECTED_DEMO_READ_ONLY":
        return _blocked("demo_readonly_state_invalid")
    account = value.get("account")
    positions = value.get("positions")
    market = value.get("market")
    if not isinstance(account, dict) or not isinstance(positions, list) or not isinstance(market, dict):
        return _blocked("demo_readonly_state_invalid")
    candles = market.get("candles")
    safe_candles = [{key: item.get(key) for key in ("time", "open", "high", "low", "close")} for item in candles if isinstance(item, dict)] if isinstance(candles, list) else []
    safe_market = {key: market.get(key) for key in ("symbol", "status", "bid", "ask", "as_of")}
    safe_market["candles"] = safe_candles
    return {"status":"CONNECTED_DEMO_READ_ONLY","as_of":value.get("as_of",""),"account":{key:account.get(key) for key in ("currency","balance","equity","margin","free_margin")},"positions":[item for item in positions if isinstance(item,dict)],"market":safe_market,"terminal_connected":True,"execution_allowed":False,"safe_to_trade":False,"real_trading":False}

def _blocked(reason: str) -> dict[str, object]:
    return {"status":"BLOCKED","reason":reason,"terminal_connected":False,"account":{},"positions":[],"market":{},"execution_allowed":False,"safe_to_trade":False,"real_trading":False}

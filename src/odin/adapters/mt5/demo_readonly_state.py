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
    if not isinstance(account, dict) or not isinstance(positions, list):
        return _blocked("demo_readonly_state_invalid")
    return {"status":"CONNECTED_DEMO_READ_ONLY","as_of":value.get("as_of",""),"account":{key:account.get(key) for key in ("currency","balance","equity","margin","free_margin")},"positions":[item for item in positions if isinstance(item,dict)],"terminal_connected":True,"execution_allowed":False,"safe_to_trade":False,"real_trading":False}

def _blocked(reason: str) -> dict[str, object]:
    return {"status":"BLOCKED","reason":reason,"terminal_connected":False,"account":{},"positions":[],"execution_allowed":False,"safe_to_trade":False,"real_trading":False}

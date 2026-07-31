"""Fail-closed local configuration for the simulated TradeDesk replay."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

ALLOWED_SYMBOLS = frozenset({"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF"})
DEFAULT_REPLAY_CONFIG = {
    "watchlist": ["EURUSD"],
    "risk_limits": {"daily_loss_limit": 100.0, "per_trade_risk_limit": 25.0, "max_position_lots": 0.05},
    "mode": "DEMO_REPLAY",
    "execution_allowed": False,
    "safe_to_trade": False,
    "real_trading": False,
}


def replay_config_path(path: str | None = None) -> Path:
    return Path(path or os.environ.get("ODIN_REPLAY_CONFIG_PATH", "/mnt/d/ODIN_LOCAL/config/replay.json"))


def load_replay_config(path: str | None = None) -> dict[str, object]:
    target = replay_config_path(path)
    if not target.is_file():
        return {**DEFAULT_REPLAY_CONFIG, "configuration_status": "DEFAULT"}
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {**DEFAULT_REPLAY_CONFIG, "configuration_status": "INVALID_BLOCKED"}
    validated = validate_replay_config(raw)
    return {**validated, "configuration_status": "LOADED" if validated["status"] == "OK" else "INVALID_BLOCKED"}


def validate_replay_config(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return _blocked("replay_config_not_object")
    if set(value) - {"watchlist", "risk_limits"}:
        return _blocked("replay_config_fields_not_allowed")
    watchlist = value.get("watchlist")
    limits = value.get("risk_limits")
    if not isinstance(watchlist, list) or not 1 <= len(watchlist) <= 6:
        return _blocked("replay_watchlist_invalid")
    if any(not isinstance(symbol, str) or symbol not in ALLOWED_SYMBOLS for symbol in watchlist):
        return _blocked("replay_watchlist_symbol_not_allowed")
    if len(set(watchlist)) != len(watchlist):
        return _blocked("replay_watchlist_duplicate")
    if not isinstance(limits, dict) or set(limits) != {"daily_loss_limit", "per_trade_risk_limit", "max_position_lots"}:
        return _blocked("replay_risk_limits_invalid")
    try:
        daily = float(limits["daily_loss_limit"])
        per_trade = float(limits["per_trade_risk_limit"])
        lots = float(limits["max_position_lots"])
    except (TypeError, ValueError):
        return _blocked("replay_risk_limits_not_numeric")
    if not 10.0 <= daily <= 500.0 or not 1.0 <= per_trade <= daily or not 0.01 <= lots <= 0.10:
        return _blocked("replay_risk_limits_out_of_bounds")
    return {
        "status": "OK", "watchlist": watchlist,
        "risk_limits": {"daily_loss_limit": daily, "per_trade_risk_limit": per_trade, "max_position_lots": lots},
        "mode": "DEMO_REPLAY", "execution_allowed": False, "safe_to_trade": False, "real_trading": False,
    }


def save_replay_config(value: object, path: str | None = None) -> dict[str, object]:
    validated = validate_replay_config(value)
    if validated["status"] != "OK":
        return validated
    target = replay_config_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    persisted = {"watchlist": validated["watchlist"], "risk_limits": validated["risk_limits"]}
    with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as temp:
        temp.write(json.dumps(persisted, indent=2, sort_keys=True) + "\n")
        temp_path = Path(temp.name)
    temp_path.replace(target)
    return {**validated, "configuration_status": "SAVED", "config_path": str(target)}


def _blocked(reason: str) -> dict[str, object]:
    return {"status": "BLOCKED", "reason": reason, "mode": "DEMO_REPLAY", "execution_allowed": False, "safe_to_trade": False, "real_trading": False}

"""Read the sanitized MT5 DEMO collector state without terminal contact."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path


MAX_OBSERVATION_AGE_SECONDS = 900


def read_demo_readonly_state(
    path: str = "/mnt/d/ODIN_LOCAL/runtime/mt5_demo_readonly.json",
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    """Return a sanitized state only while its collector timestamp is fresh."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _blocked("demo_readonly_state_missing")
    if not isinstance(value, dict) or value.get("status") != "CONNECTED_DEMO_READ_ONLY":
        return _blocked("demo_readonly_state_invalid")
    observed_at = _parse_observed_at(value.get("as_of"))
    if observed_at is None:
        return _blocked("demo_readonly_state_invalid_timestamp")
    current = now or datetime.now(timezone.utc)
    age_seconds = int((current - observed_at).total_seconds())
    if age_seconds < 0 or age_seconds > MAX_OBSERVATION_AGE_SECONDS:
        return _blocked("demo_readonly_state_stale", as_of=observed_at.isoformat(), age_seconds=age_seconds)
    account = value.get("account")
    positions = value.get("positions")
    market = value.get("market")
    if not isinstance(account, dict) or not isinstance(positions, list) or not isinstance(market, dict):
        return _blocked("demo_readonly_state_invalid")
    candles = market.get("candles")
    safe_candles = [
        {key: item.get(key) for key in ("time", "open", "high", "low", "close")}
        for item in candles
        if isinstance(item, dict)
    ] if isinstance(candles, list) else []
    safe_market = {key: market.get(key) for key in ("symbol", "status", "bid", "ask", "as_of")}
    safe_market["candles"] = safe_candles
    return {
        "status": "CONNECTED_DEMO_READ_ONLY",
        "as_of": observed_at.isoformat(),
        "age_seconds": age_seconds,
        "fresh": True,
        "account": {key: account.get(key) for key in ("currency", "balance", "equity", "margin", "free_margin")},
        "positions": [item for item in positions if isinstance(item, dict)],
        "market": safe_market,
        "terminal_connected": True,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _parse_observed_at(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _blocked(reason: str, *, as_of: str = "", age_seconds: int | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "status": "BLOCKED",
        "reason": reason,
        "as_of": as_of,
        "fresh": False,
        "terminal_connected": False,
        "account": {},
        "positions": [],
        "market": {},
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }
    if age_seconds is not None:
        result["age_seconds"] = age_seconds
    return result

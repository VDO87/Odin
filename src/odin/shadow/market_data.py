"""Adapters that normalize read-only MT5, P0 and replay data into MarketBar."""

from __future__ import annotations

from odin.contracts.shadow_intelligence import MarketBar


def from_mt5_observation(value: dict[str, object]) -> list[MarketBar]:
    """Normalize sanitized read-only MT5 state; invalid/stale data stays degraded."""
    market = value.get("market")
    if not isinstance(market, dict):
        return []
    source = "MT5_DEMO_READ_ONLY"
    provenance = str(value.get("content_hash", "UNAVAILABLE"))
    quality = "VALIDATED" if value.get("status") == "CONNECTED_DEMO_READ_ONLY" and value.get("fresh") is True and market.get("status") == "OK" else "DEGRADED"
    result = []
    for item in market.get("candles", []):
        if not isinstance(item, dict):
            continue
        try:
            result.append(MarketBar(str(market.get("symbol", "")), "M15", str(item["time"]), _number(item["open"]), _number(item["high"]), _number(item["low"]), _number(item["close"]), 0.0, _spread(market), source, provenance, quality))
        except (KeyError, TypeError, ValueError):
            return []
    return result


def from_replay_candles(candles: list[dict[str, object]], *, symbol: str, timeframe: str) -> list[MarketBar]:
    """Normalize local replay candles without introducing a provider branch in strategy."""
    result = []
    for item in candles:
        try:
            result.append(MarketBar(symbol, timeframe, str(item["timestamp"]), _number(item["open"]), _number(item["high"]), _number(item["low"]), _number(item["close"]), _number(item.get("volume", 0)), _spread(item), "LOCAL_REPLAY", "replay_fixture", "VALIDATED"))
        except (KeyError, TypeError, ValueError):
            return []
    return result


def _spread(value: dict[str, object]) -> float | None:
    raw = value.get("spread")
    try:
        return _number(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _number(value: object) -> float:
    if not isinstance(value, (int, float, str)):
        raise ValueError("market_bar_number_invalid")
    return float(value)

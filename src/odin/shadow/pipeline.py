"""Deterministic MarketState, risk and decision pipeline for supervised shadow."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Iterable

from odin.contracts.shadow_intelligence import MarketBar, MarketState

_ALLOWED_SIGNALS = {"BUY", "SELL", "HOLD", "NO_TRADE", "BLOCKED"}


def bars_hash(bars: Iterable[MarketBar]) -> str:
    value = [bar.to_dict() for bar in bars]
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_market_state(bars: list[MarketBar], *, now_utc: datetime | None = None) -> MarketState:
    """Calculate factual state only from supplied bars; no provider-specific logic."""
    if not bars:
        return MarketState("", "", "", "MISSING", "INVALID", "UNKNOWN", 0.0, None, "UNKNOWN", "UNAVAILABLE", "UNRECONCILED", bars_hash([]))
    last = bars[-1]
    try:
        as_of = datetime.fromisoformat(last.timestamp_utc.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        as_of = datetime.min.replace(tzinfo=UTC)
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    freshness = "FRESH" if 0 <= (now - as_of).total_seconds() <= 20 * 60 else "STALE"
    quality = "VALID" if all(bar.quality_status == "VALIDATED" for bar in bars) else "DEGRADED"
    closes = [bar.close for bar in bars]
    short = sum(closes[-3:]) / min(3, len(closes))
    long = sum(closes[-5:]) / min(5, len(closes))
    trend = "UP" if short > long else "DOWN" if short < long else "FLAT"
    volatility = sum(bar.high - bar.low for bar in bars[-5:]) / min(5, len(bars))
    spreads = [bar.spread for bar in bars if bar.spread is not None]
    spread = sum(spreads) / len(spreads) if spreads else None
    hour = as_of.hour
    session = "ASIA" if hour < 7 else "LONDON" if hour < 13 else "NEW_YORK" if hour < 21 else "OFF_HOURS"
    available = "AVAILABLE" if freshness == "FRESH" and quality == "VALID" else "DEGRADED"
    return MarketState(last.symbol, last.timeframe, last.timestamp_utc, freshness, quality, trend, round(volatility, 8), spread, session, available, "RECONCILED_SINGLE_SOURCE", bars_hash(bars))


def evaluate_shadow_risk(state: MarketState, *, kill_switch: bool = False, max_spread: float = 0.00050) -> dict[str, object]:
    """Risk is deterministic and can only permit observation, never execution."""
    reasons: list[str] = []
    if kill_switch:
        reasons.append("kill_switch_engaged")
    if state.freshness != "FRESH":
        reasons.append("stale_data")
    if state.data_quality != "VALID":
        reasons.append("bad_data")
    if state.availability != "AVAILABLE":
        reasons.append("missing_or_unavailable_data")
    if state.source_reconciliation_status != "RECONCILED_SINGLE_SOURCE":
        reasons.append("invalid_reconciliation")
    if state.spread_proxy is not None and state.spread_proxy > max_spread:
        reasons.append("excessive_spread")
    status = "KILL" if kill_switch else "BLOCK" if reasons else "ALLOW_SHADOW"
    return {"risk_status": status, "reason_codes": reasons, "execution_allowed": False, "safe_to_trade": False, "real_trading": False}


def shadow_decision(bars: list[MarketBar], *, strategy_id: str = "trend_mean_v1", now_utc: datetime | None = None, kill_switch: bool = False) -> dict[str, object]:
    state = build_market_state(bars, now_utc=now_utc)
    risk = evaluate_shadow_risk(state, kill_switch=kill_switch)
    signal = "BLOCKED" if risk["risk_status"] != "ALLOW_SHADOW" else "BUY" if state.trend == "UP" else "SELL" if state.trend == "DOWN" else "HOLD"
    assert signal in _ALLOWED_SIGNALS
    risk_reasons = risk["reason_codes"]
    assert isinstance(risk_reasons, list)
    seed = {"strategy_id": strategy_id, "state": state.to_dict(), "signal": signal, "risk": risk}
    decision_id = hashlib.sha256(json.dumps(seed, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"status": "OK", "mode": "SHADOW", "decision_id": decision_id, "timestamp": state.as_of_utc, "symbol": state.symbol, "timeframe": state.timeframe, "strategy_id": strategy_id, "strategy_version": "1", "signal": signal, "confidence": 1.0 if signal in {"BUY", "SELL"} else 0.0, "reason_codes": risk_reasons or [f"trend_{state.trend.lower()}"], "market_data_hash": state.market_data_hash, "market_state": state.to_dict(), "data_quality": state.data_quality, "freshness": state.freshness, "risk_result": risk, "expiry": state.as_of_utc, "execution_allowed": False, "safe_to_trade": False, "real_trading": False}

"""Build a non-order TradeProposal from one accepted ShadowDecision."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json

from odin.contracts.demo_execution import TradeProposal


def build_trade_proposal(
    decision: dict[str, object],
    *,
    entry_reference: float,
    stop_loss: float,
    take_profit: float,
    volume: float = 0.01,
    now_utc: datetime | None = None,
    lifetime_seconds: int = 60,
) -> dict[str, object]:
    """Return a proposal only for BUY/SELL; it has no broker capability."""
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    reasons: list[str] = []
    signal = decision.get("signal")
    if signal not in {"BUY", "SELL"}:
        reasons.append("decision_not_actionable")
    if decision.get("execution_allowed") is not False:
        reasons.append("shadow_decision_execution_boundary_invalid")
    for key in ("decision_id", "strategy_id", "strategy_version", "market_data_hash"):
        if not isinstance(decision.get(key), str) or not decision.get(key):
            reasons.append(f"missing_{key}")
    if decision.get("data_quality") != "VALID":
        reasons.append("proposal_bad_data")
    if decision.get("freshness") != "FRESH":
        reasons.append("proposal_stale_data")
    if any(value <= 0 for value in (entry_reference, stop_loss, take_profit, volume)):
        reasons.append("proposal_invalid_price_or_volume")
    if reasons:
        return _blocked(reasons)
    timestamp = now.isoformat(timespec="seconds")
    expiry = (now + timedelta(seconds=lifetime_seconds)).isoformat(timespec="seconds")
    seed = {
        "decision_id": decision["decision_id"],
        "timestamp_utc": timestamp,
        "symbol": decision.get("symbol", ""),
        "side": signal,
        "volume": volume,
        "entry_reference": entry_reference,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "market_data_hash": decision["market_data_hash"],
    }
    proposal_id = hashlib.sha256(
        json.dumps(seed, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    decision_reasons = decision.get("reason_codes")
    proposal = TradeProposal(
        proposal_id=proposal_id,
        decision_id=str(decision["decision_id"]),
        timestamp_utc=timestamp,
        symbol=str(decision.get("symbol", "")),
        side=str(signal),
        volume=volume,
        entry_reference=entry_reference,
        stop_loss=stop_loss,
        take_profit=take_profit,
        strategy_id=str(decision["strategy_id"]),
        strategy_version=str(decision["strategy_version"]),
        reason_codes=tuple(str(item) for item in decision_reasons)
        if isinstance(decision_reasons, list)
        else (),
        market_data_hash=str(decision["market_data_hash"]),
        data_quality=str(decision.get("data_quality")),
        freshness=str(decision.get("freshness")),
        expiry=expiry,
    )
    return {
        "status": "PROPOSED",
        "proposal": proposal,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _blocked(reasons: list[str]) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "reason_codes": reasons,
        "proposal": None,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }

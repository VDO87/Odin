"""Deterministic financial risk evaluation for DEMO scope only."""

from __future__ import annotations

from odin.contracts.demo_execution import DemoAccountEvidence, DemoRiskLimits, TradeProposal


def estimated_max_loss(proposal: TradeProposal, evidence: DemoAccountEvidence) -> float | None:
    if evidence.trade_tick_size <= 0 or evidence.trade_tick_value_loss <= 0:
        return None
    ticks_to_stop = abs(proposal.entry_reference - proposal.stop_loss) / evidence.trade_tick_size
    return round(ticks_to_stop * evidence.trade_tick_value_loss * proposal.volume, 2)


def evaluate_demo_risk(
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    *,
    limits: DemoRiskLimits | None = None,
) -> dict[str, object]:
    """Return ALLOW_DEMO only for conservative DEMO evidence; never a global unlock."""
    policy = limits or DemoRiskLimits()
    reasons: list[str] = []
    loss = estimated_max_loss(proposal, evidence)
    if evidence.kill_switch_engaged:
        reasons.append("kill_switch_engaged")
    if proposal.symbol != "EURUSD" or evidence.symbol != "EURUSD":
        reasons.append("symbol_not_authorized")
    if proposal.data_quality != "VALID":
        reasons.append("bad_data")
    if evidence.market_time_status == "BLOCKED":
        reasons.extend(evidence.market_time_reason_codes or ("future_market_timestamp",))
    elif proposal.freshness != "FRESH" or not evidence.data_fresh:
        reasons.append("stale_data")
    if evidence.data_age_seconds < -policy.allowed_future_clock_skew_seconds:
        reasons.extend(("future_market_timestamp", "clock_skew_detected"))
    elif evidence.data_age_seconds > policy.stale_data_threshold_seconds:
        reasons.append("stale_data_threshold_exceeded")
    if evidence.spread > policy.max_spread:
        reasons.append("excessive_spread")
    if evidence.daily_realized_pnl <= -policy.max_daily_demo_loss:
        reasons.append("daily_demo_loss_limit")
    if evidence.completed_trades_today >= policy.max_completed_trades_per_day:
        reasons.append("daily_completed_trade_limit")
    if evidence.drawdown_percent >= policy.max_drawdown_percent:
        reasons.append("demo_drawdown_limit")
    if proposal.volume > policy.max_position_size:
        reasons.append("max_position_size_exceeded")
    if evidence.open_positions >= policy.max_simultaneous_positions:
        reasons.append("position_limit_reached")
    if evidence.active_orders >= policy.max_simultaneous_orders:
        reasons.append("order_limit_reached")
    if evidence.free_margin < policy.minimum_free_margin:
        reasons.append("minimum_free_margin_not_met")
    if loss is None:
        reasons.append("risk_estimate_unavailable")
    elif loss > policy.max_risk_per_trade:
        reasons.append("max_risk_per_trade_exceeded")
    reasons = list(dict.fromkeys(reasons))
    status = "KILL" if evidence.kill_switch_engaged else "BLOCK" if reasons else "ALLOW_DEMO"
    return {
        "status": status,
        "risk_approved": status == "ALLOW_DEMO",
        "reason_codes": reasons,
        "estimated_max_loss": loss,
        "limits": policy.to_dict(),
        "execution_allowed_scope": "DEMO" if status == "ALLOW_DEMO" else "NONE",
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }

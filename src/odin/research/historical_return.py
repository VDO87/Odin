"""Small deterministic historical-return report, not a trading strategy."""

from __future__ import annotations


def historical_return_report(
    closes: list[float], *, transaction_cost_bps: float = 10.0
) -> dict[str, object]:
    """Report one hypothetical historical path with conservative round-trip costs."""
    if len(closes) < 2 or any(not isinstance(value, (int, float)) or value <= 0 for value in closes):
        return _blocked("at_least_two_positive_close_prices_required")
    if transaction_cost_bps < 0:
        return _blocked("transaction_cost_bps_must_be_non_negative")

    gross_return = (float(closes[-1]) / float(closes[0])) - 1.0
    net_return = gross_return - (2 * (transaction_cost_bps / 10_000.0))
    peak = float(closes[0])
    max_drawdown = 0.0
    for close in closes:
        peak = max(peak, float(close))
        max_drawdown = min(max_drawdown, (float(close) / peak) - 1.0)
    return {
        "status": "OK",
        "component": "historical_return_report",
        "mode": "RESEARCH_OBSERVATION_ONLY",
        "sample_count": len(closes),
        "gross_return": round(gross_return, 8),
        "transaction_cost_bps": transaction_cost_bps,
        "net_return_after_costs": round(net_return, 8),
        "max_drawdown": round(max_drawdown, 8),
        "not_investment_advice": True,
        "decision_generated": False,
        "proposal_generated": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
        "reason": "local_historical_observation_only",
    }


def _blocked(reason: str) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "component": "historical_return_report",
        "mode": "RESEARCH_OBSERVATION_ONLY",
        "not_investment_advice": True,
        "decision_generated": False,
        "proposal_generated": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
        "reason": reason,
    }

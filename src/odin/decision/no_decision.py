"""Blocked decision intent builder for A9."""

from __future__ import annotations

from odin.contracts.decision_intent import DecisionIntent


DEFAULT_BLOCKERS = [
    "strategy_observe_only",
    "risk_engine_ready_blocking",
    "real_trading_disabled",
    "execution_disabled",
]


def _text_field(data: dict[str, object], key: str, default: str) -> str:
    value = data.get(key, default)
    return value if isinstance(value, str) else str(value)


def build_no_decision_intent(strategy: dict[str, object]) -> dict[str, object]:
    intent = DecisionIntent(
        component="decision_intent",
        status="OK",
        decision_intent_status="NO_DECISION",
        decision_intent_mode="INTENT_SKELETON",
        symbol=_text_field(strategy, "symbol", "EURUSD"),
        source=_text_field(strategy, "source", "mock"),
        strategy_name=_text_field(strategy, "strategy_name", "baseline_observer"),
        strategy_status=_text_field(strategy, "strategy_status", "READY_NO_DECISION"),
        data_quality_status=_text_field(strategy, "data_quality_status", "OK"),
        read_only=True,
        safe_to_trade=False,
        real_trading=False,
        execution_allowed=False,
        decision_generated=False,
        proposal_generated=False,
        risk_approved=False,
        reason="decision_intent_skeleton_blocked",
        blockers=list(DEFAULT_BLOCKERS),
        notes=[
            "Decision intent reads strategy status and remains blocked.",
            "No market direction is created in A9.",
        ],
    )
    return intent.to_dict()

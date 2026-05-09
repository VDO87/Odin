from market import (
    ContextState,
    FeedIntegrityState,
    MarketAssessment,
    MarketReadiness,
    MarketState,
    SpreadState,
)
from risk import RiskDecision, RiskEvaluator, RiskInput, RiskState
from shared.enums import OperationalMode
from shared.utils import utc_now


def make_market_assessment() -> MarketAssessment:
    return MarketAssessment(
        market_state=MarketState.VALID,
        context_state=ContextState.FAVORABLE,
        readiness_state=MarketReadiness.READY,
        feed_integrity_state=FeedIntegrityState.OK,
        last_valid_update_utc=utc_now(),
        spread_state=SpreadState.NORMAL,
    )


def test_risk_assessment_payload_contains_core_contract_fields() -> None:
    assessment = RiskEvaluator().evaluate(
        RiskInput(
            market=make_market_assessment(),
            current_daily_pnl=100.0,
            max_daily_loss=500.0,
        )
    )

    event = assessment.to_core_event()
    payload = event.payload

    assert assessment.risk_state == RiskState.NORMAL
    assert assessment.risk_decision == RiskDecision.ALLOW
    assert event.event_type == "EV-RISK-ALLOW"
    assert payload["risk_state"] == "RS-10"
    assert payload["risk_decision"] == "ALLOW"
    assert payload["allowance_class"] == "ALLOW"
    assert payload["kill_active"] is False
    assert payload["dominant_risk_reason"] == "risk_within_limits"
    assert payload["cooldown_active"] is False
    assert "evaluated_at_utc" in payload


def test_risk_evaluator_kill_has_precedence() -> None:
    assessment = RiskEvaluator().evaluate(
        RiskInput(
            market=make_market_assessment(),
            kill_switch_active=True,
        )
    )

    assert assessment.risk_state == RiskState.KILL_ACTIVE
    assert assessment.risk_decision == RiskDecision.KILL
    assert assessment.kill_active is True
    assert assessment.to_core_event().event_type == "EV-KILL-ACTIVE"


def test_real_mode_without_operation_impact_restricts_risk() -> None:
    assessment = RiskEvaluator().evaluate(
        RiskInput(
            market=make_market_assessment(),
            current_mode=OperationalMode.REAL,
            expected_operation_impact=None,
            max_risk_per_operation=100.0,
        )
    )

    assert assessment.risk_state == RiskState.RESTRICTED
    assert assessment.risk_decision == RiskDecision.RESTRICT
    assert assessment.dominant_risk_reason == "real_mode_requires_operation_impact"


def test_real_mode_operation_limit_can_block() -> None:
    assessment = RiskEvaluator().evaluate(
        RiskInput(
            market=make_market_assessment(),
            current_mode=OperationalMode.REAL,
            expected_operation_impact=125.0,
            max_risk_per_operation=100.0,
        )
    )

    assert assessment.risk_state == RiskState.BLOCKED
    assert assessment.risk_decision == RiskDecision.BLOCK
    assert assessment.dominant_risk_reason == "real_mode_operation_limit_exceeded"

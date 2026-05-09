from decision import DecisionCandidate, DecisionEngine
from shared.contracts import DecisionInputSnapshot
from shared.enums import DecisionOutput, DecisionState, GlobalState, OperationalMode


def make_snapshot(
    *,
    global_state: GlobalState = GlobalState.READY,
    market_state: str = "MS-10",
    context_class: str = "MC-10",
    feed_integrity_state: str = "FI-10",
    risk_state: str = "ALLOW",
    kill_active: bool = False,
    active_block_count: int = 0,
) -> DecisionInputSnapshot:
    return DecisionInputSnapshot(
        global_state=global_state,
        current_mode=OperationalMode.DEMO,
        market_state=market_state,
        context_class=context_class,
        feed_integrity_state=feed_integrity_state,
        risk_state=risk_state,
        kill_active=kill_active,
        active_block_vector_summary={"active_block_count": active_block_count},
        instrument_snapshot_ref="market-snapshot-1",
        decision_config_version="decision-v1",
    )


def test_decision_engine_emits_restricted_intent_with_audit_rationale() -> None:
    evaluation = DecisionEngine().evaluate(
        make_snapshot(context_class="MC-30", risk_state="RESTRICT"),
        [
            DecisionCandidate(
                hypothesis_id="hyp-1",
                tactic_id="tactic-breakout",
                instrument_id="EURUSD",
                side="BUY",
                score_value=0.92,
                min_score_threshold=0.8,
                reason_summary="breakout selected",
                price_reference=1.1000,
            ),
            DecisionCandidate(
                hypothesis_id="hyp-2",
                tactic_id="tactic-mean-reversion",
                instrument_id="EURUSD",
                side="SELL",
                score_value=0.81,
                min_score_threshold=0.8,
                reason_summary="secondary idea",
                price_reference=1.0998,
            ),
        ],
        ttl_ms=3000,
        max_slippage=0.0002,
    )

    assert evaluation.result.decision_state == DecisionState.INTENT_EMITTED
    assert evaluation.result.decision_output == DecisionOutput.RESTRICTED
    assert evaluation.intent is not None
    assert evaluation.intent.intent_id == evaluation.result.intent_id
    assert set(evaluation.intent.restriction_flags) >= {"context_sensitive", "risk_restricted"}
    assert evaluation.rationale.selected_tactic_id == "tactic-breakout"
    assert evaluation.rationale.selected_hypothesis_id == "hyp-1"
    assert len(evaluation.rationale.evaluated_candidates) == 2


def test_decision_engine_blocks_when_market_or_risk_are_incompatible() -> None:
    evaluation = DecisionEngine().evaluate(
        make_snapshot(market_state="MS-40", risk_state="BLOCK"),
        [
            DecisionCandidate(
                hypothesis_id="hyp-1",
                tactic_id="tactic-breakout",
                instrument_id="EURUSD",
                side="BUY",
                score_value=0.92,
                min_score_threshold=0.8,
                reason_summary="breakout selected",
                price_reference=1.1000,
            )
        ],
        ttl_ms=3000,
        max_slippage=0.0002,
    )

    assert evaluation.result.decision_state == DecisionState.BLOCKED_EXTERNALLY
    assert evaluation.result.decision_output == DecisionOutput.BLOCKED
    assert evaluation.result.intent_emitted is False
    assert evaluation.intent is None
    assert evaluation.rationale.blocked_by_external is True

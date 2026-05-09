from shared.contracts import (
    DecisionCycleResult,
    DecisionInputSnapshot,
    ExecutionIntent,
    ExecutionSnapshot,
)
from shared.enums import (
    DecisionOutput,
    DecisionState,
    ExecutionFinalResult,
    ExecutionInitialResult,
    ExecutionState,
    GlobalState,
    OperationalMode,
)
from shared.utils import utc_now


def test_decision_input_snapshot_round_trip() -> None:
    snapshot = DecisionInputSnapshot(
        global_state=GlobalState.MONITORING,
        current_mode=OperationalMode.DEMO,
        market_state="MS-10",
        context_class="MC-10",
        feed_integrity_state="FI-10",
        risk_state="ALLOW",
        kill_active=False,
        active_block_vector_summary={"active_block_count": 0},
        instrument_snapshot_ref="market-snapshot-1",
        decision_config_version="decision-v1",
    )

    restored = DecisionInputSnapshot.from_dict(snapshot.to_dict())

    assert restored.snapshot_id == snapshot.snapshot_id
    assert restored.global_state == GlobalState.MONITORING
    assert restored.current_mode == OperationalMode.DEMO


def test_decision_cycle_result_builds_core_state_update() -> None:
    result = DecisionCycleResult(
        decision_cycle_id="cycle-1",
        snapshot_id="snapshot-1",
        decision_state=DecisionState.INTENT_EMITTED,
        decision_output=DecisionOutput.CANDIDATE_SELECTED,
        intent_emitted=True,
        blocked_by_external=False,
        reason_summary="candidate selected",
        selected_tactic_id="tactic-breakout",
        intent_id="intent-1",
    )

    payload = result.to_state_update().to_core_payload()

    assert payload["decision_state"] == "DS-70"
    assert payload["decision_output"] == "CANDIDATE_SELECTED"
    assert payload["selected_tactic_id"] == "tactic-breakout"
    assert payload["intent_id"] == "intent-1"


def test_execution_intent_create_sets_expiry_and_dual_restriction_keys() -> None:
    intent = ExecutionIntent.create(
        intent_id="intent-1",
        decision_cycle_id="cycle-1",
        ttl_ms=3000,
        instrument_id="EURUSD",
        side="BUY",
        target_order_type="MARKET",
        max_slippage=0.0002,
        market_snapshot_ref="market-snapshot-1",
        risk_snapshot_ref="risk-snapshot-1",
        decision_config_version="decision-v1",
        restriction_flags=("cooldown", "reduced_size"),
    )

    payload = intent.to_dict()
    restored = ExecutionIntent.from_dict(payload)

    assert payload["ttl_ms"] == 3000
    assert payload["expires_at_utc"] is not None
    assert payload["restriction_flags"] == ["cooldown", "reduced_size"]
    assert payload["restrictions"] == ["cooldown", "reduced_size"]
    assert restored.intent_id == "intent-1"
    assert restored.decision_cycle_id == "cycle-1"


def test_execution_snapshot_builds_core_payload_with_execution_state_alias() -> None:
    snapshot = ExecutionSnapshot(
        intent_id="intent-1",
        decision_cycle_id="cycle-1",
        request_id="request-1",
        exec_state=ExecutionState.SUBMITTED,
        initial_result=ExecutionInitialResult.ACCEPTED,
        final_result=ExecutionFinalResult.PENDING_RESOLUTION,
        created_at_utc=utc_now(),
        updated_at_utc=utc_now(),
        divergence_flag=False,
        reason_summary="submission accepted",
    )

    payload = snapshot.to_state_update().to_core_payload()

    assert payload["execution_state"] == "ES-50"
    assert payload["exec_state"] == "ES-50"
    assert payload["execution_result"] == "EX-40"
    assert payload["intent_id"] == "intent-1"
    assert payload["decision_cycle_id"] == "cycle-1"

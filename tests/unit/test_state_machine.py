from core.blocks import BlockManager
from core.guards import TransitionGuardEngine
from core.state_machine import CoreStateMachine
from shared.contracts import ActiveBlockVector, BlockEntry, CoreEventEnvelope, GlobalStateSnapshot
from shared.enums import BlockCode, EventType, GlobalState, IntegrityClass, OperationalMode, ReadinessClass, Severity


def make_snapshot(state: GlobalState) -> GlobalStateSnapshot:
    return GlobalStateSnapshot.create(
        state_code=state,
        mode_code=OperationalMode.DEMO,
        last_transition_event="seed",
        readiness_class=ReadinessClass.MONITORING,
        integrity_class=IntegrityClass.OK,
        kill_active=False,
        active_block_count=0,
        recovery_required=False,
    )


def test_ready_to_active_on_exec_confirmed() -> None:
    machine = CoreStateMachine()
    event = CoreEventEnvelope(
        event_type=EventType.EXEC_CONFIRMED.value,
        source_module="EXEC",
        severity=Severity.INFO,
        payload={},
    )

    snapshot = machine.apply_event(event, make_snapshot(GlobalState.READY), ActiveBlockVector.empty(), TransitionGuardEngine())

    assert snapshot.state_code == GlobalState.ACTIVE


def test_startup_to_active_is_rejected_by_guard() -> None:
    guard = TransitionGuardEngine()
    event = CoreEventEnvelope(
        event_type=EventType.EXEC_CONFIRMED.value,
        source_module="EXEC",
        severity=Severity.INFO,
        payload={},
    )

    result = guard.evaluate(
        event,
        make_snapshot(GlobalState.STARTUP),
        GlobalState.ACTIVE,
        ActiveBlockVector.empty(),
    )

    assert result.allowed is False
    assert result.blocking_reason_code == "forbidden_state_transition"


def test_resume_is_rejected_while_manual_block_is_active() -> None:
    guard = TransitionGuardEngine()
    manager = BlockManager()
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.MANUAL,
            source_module="DASH",
            severity=Severity.ERROR,
            reason_code="manual_hold",
            manual_clear_required=True,
            clearable_by_recovery=False,
        )
    )
    event = CoreEventEnvelope(
        event_type=EventType.RESUME.value,
        source_module="DASH",
        severity=Severity.INFO,
        payload={},
    )

    result = guard.evaluate(
        event,
        make_snapshot(GlobalState.PAUSED),
        GlobalState.MONITORING,
        manager.as_vector(),
    )

    assert result.allowed is False
    assert result.blocking_reason_code == "manual_block_active"


def test_active_transition_uses_kill_precedence_over_manual_and_recovery() -> None:
    guard = TransitionGuardEngine()
    manager = BlockManager()
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.RECOVERY_PENDING,
            source_module="RECOVERY",
            severity=Severity.ERROR,
            reason_code="recovery_pending",
            manual_clear_required=False,
            clearable_by_recovery=True,
        )
    )
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.MANUAL,
            source_module="DASH",
            severity=Severity.ERROR,
            reason_code="manual_hold",
            manual_clear_required=True,
            clearable_by_recovery=False,
        )
    )
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.KILL,
            source_module="RISK",
            severity=Severity.CRITICAL,
            reason_code="kill_active",
            manual_clear_required=True,
            clearable_by_recovery=False,
        )
    )
    event = CoreEventEnvelope(
        event_type=EventType.EXEC_CONFIRMED.value,
        source_module="EXEC",
        severity=Severity.INFO,
        payload={},
    )

    result = guard.evaluate(
        event,
        make_snapshot(GlobalState.READY),
        GlobalState.ACTIVE,
        manager.as_vector(),
    )

    assert result.allowed is False
    assert result.blocking_reason_code == "kill_active"


def test_active_transition_uses_manual_precedence_over_recovery_pending() -> None:
    guard = TransitionGuardEngine()
    manager = BlockManager()
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.RECOVERY_PENDING,
            source_module="RECOVERY",
            severity=Severity.ERROR,
            reason_code="recovery_pending",
            manual_clear_required=False,
            clearable_by_recovery=True,
        )
    )
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.MANUAL,
            source_module="DASH",
            severity=Severity.ERROR,
            reason_code="manual_hold",
            manual_clear_required=True,
            clearable_by_recovery=False,
        )
    )
    event = CoreEventEnvelope(
        event_type=EventType.EXEC_CONFIRMED.value,
        source_module="EXEC",
        severity=Severity.INFO,
        payload={},
    )

    result = guard.evaluate(
        event,
        make_snapshot(GlobalState.READY),
        GlobalState.ACTIVE,
        manager.as_vector(),
    )

    assert result.allowed is False
    assert result.blocking_reason_code == "manual_block_active"


def test_maintenance_exit_is_rejected_while_manual_block_is_active() -> None:
    guard = TransitionGuardEngine()
    manager = BlockManager()
    manager.apply_block(
        BlockEntry(
            block_code=BlockCode.MANUAL,
            source_module="DASH",
            severity=Severity.ERROR,
            reason_code="manual_hold",
            manual_clear_required=True,
            clearable_by_recovery=False,
        )
    )
    event = CoreEventEnvelope(
        event_type=EventType.MAINTENANCE_EXIT.value,
        source_module="DASH",
        severity=Severity.INFO,
        payload={},
    )

    result = guard.evaluate(
        event,
        make_snapshot(GlobalState.MAINTENANCE),
        GlobalState.IDLE,
        manager.as_vector(),
    )

    assert result.allowed is False
    assert result.blocking_reason_code == "manual_block_active"

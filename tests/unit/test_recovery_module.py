from pathlib import Path

from persistence.sqlite_state_store import SQLiteStateStore
from recovery import (
    ObservedStateSnapshot,
    RecoveryIncidentType,
    RecoveryOrchestrator,
    RecoveryResultCode,
)
from shared.contracts import ActiveBlockVector, BlockEntry, PersistentKillState
from shared.enums import BlockCode, Severity


def test_recovery_requires_manual_intervention_when_confidence_is_unsafe(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state" / "core_state.db")
    store.initialize()

    evaluation = RecoveryOrchestrator(store).recover(
        incident_type=RecoveryIncidentType.EXEC_DIVERGENCE,
        observed_state=ObservedStateSnapshot(
            module_availability_map={"MARKET": True, "RISK": True, "EXEC": False},
            kill_active_observed=False,
        ),
        trigger_event_id="exec-divergence-1",
    )

    assert evaluation.result.result_code == RecoveryResultCode.MANUAL_REQUIRED
    assert evaluation.result.manual_intervention_required is True
    assert evaluation.result.event_type == "EV-RECOVERY-INTERVENTION-REQUIRED"


def test_recovery_snapshot_is_persisted_and_readable(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state" / "core_state.db")
    store.initialize()

    evaluation = RecoveryOrchestrator(store).recover(
        incident_type=RecoveryIncidentType.UNEXPECTED_RESTART,
        observed_state=ObservedStateSnapshot(
            module_availability_map={"MARKET": True, "RISK": True, "EXEC": True},
            market_state="MS-10",
            risk_state="ALLOW",
            exec_state_summary="ES-10",
            kill_active_observed=False,
        ),
        trigger_event_id="restart-1",
    )
    restored = store.read_latest_recovery_snapshot()

    assert restored is not None
    assert restored.recovery_snapshot_id == evaluation.snapshot.recovery_snapshot_id
    assert restored.result.recovery_id == evaluation.result.recovery_id
    assert restored.result.result_code == evaluation.result.result_code


def test_recovery_timeout_with_missing_module_is_inconclusive(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state" / "core_state.db")
    store.initialize()

    evaluation = RecoveryOrchestrator(store).recover(
        incident_type=RecoveryIncidentType.CRITICAL_MODULE_TIMEOUT,
        observed_state=ObservedStateSnapshot(
            module_availability_map={"MARKET": True, "RISK": True, "EXEC": False},
            market_state="MS-10",
            risk_state="ALLOW",
            exec_state_summary="ES-60",
            kill_active_observed=False,
        ),
        trigger_event_id="timeout-1",
    )

    assert evaluation.result.result_code == RecoveryResultCode.INCONCLUSIVE
    assert evaluation.result.manual_intervention_required is True
    assert evaluation.result.event_type == "EV-RECOVERY-FAIL"


def test_recovery_is_blocked_by_kill_precedence_when_kill_is_persisted(tmp_path: Path) -> None:
    store = SQLiteStateStore(tmp_path / "state" / "core_state.db")
    store.initialize()
    store.write_kill_state(
        PersistentKillState(
            is_active=True,
            source_module="RISK",
            reason_code="kill_active",
        )
    )

    evaluation = RecoveryOrchestrator(store).recover(
        incident_type=RecoveryIncidentType.UNEXPECTED_RESTART,
        observed_state=ObservedStateSnapshot(
            module_availability_map={"MARKET": True, "RISK": True, "EXEC": True},
            market_state="MS-10",
            risk_state="ALLOW",
            exec_state_summary="ES-10",
            kill_active_observed=True,
        ),
        trigger_event_id="restart-kill-1",
    )

    assert evaluation.result.result_code == RecoveryResultCode.MANUAL_REQUIRED
    assert evaluation.result.result_summary == "recovery_blocked_by_kill_precedence"


def test_recovery_is_blocked_by_manual_precedence_when_manual_block_is_persisted(
    tmp_path: Path,
) -> None:
    store = SQLiteStateStore(tmp_path / "state" / "core_state.db")
    store.initialize()
    manual_vector = ActiveBlockVector(
        blocks=(
            BlockEntry(
                block_code=BlockCode.MANUAL,
                source_module="DASH",
                severity=Severity.ERROR,
                reason_code="manual_hold",
                manual_clear_required=True,
                clearable_by_recovery=False,
            ),
        ),
        dominant_block_reason="manual_hold",
        dominant_block_priority=90,
        manual_clear_required=True,
    )
    store.write_block_vector(manual_vector)

    evaluation = RecoveryOrchestrator(store).recover(
        incident_type=RecoveryIncidentType.MANUAL_RECOVERY_REQUEST,
        observed_state=ObservedStateSnapshot(
            module_availability_map={"MARKET": True, "RISK": True, "EXEC": True},
            market_state="MS-10",
            risk_state="ALLOW",
            exec_state_summary="ES-10",
            kill_active_observed=False,
        ),
        trigger_event_id="manual-precedence-1",
    )

    assert evaluation.result.result_code == RecoveryResultCode.MANUAL_REQUIRED
    assert evaluation.result.result_summary == "recovery_blocked_by_manual_precedence"

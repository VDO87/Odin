from pathlib import Path

from core.runtime import CoreRuntimeController
from dash import CoreDashBridge, DashboardControlActionRequest, DashboardPermissionContext
from market import MarketEvaluator, MarketSampleInput
from persistence.sqlite_state_store import SQLiteStateStore
from recovery import ObservedStateSnapshot, RecoveryIncidentType, RecoveryOrchestrator, RecoveryResultCode
from shared.config import OdinSettings
from shared.contracts import CoreEventEnvelope
from shared.enums import BlockCode, GlobalState, Severity
from shared.utils import utc_now


def write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "odin.local.toml"
    config_path.write_text(
        """
[core]
startup_timeout_ms = 15000
event_queue_max_size = 2048
heartbeat_timeout_ms = 500
heartbeat_grace_count = 1
allow_real_mode = false
recovery_required_on_unclean_shutdown = true
persist_on_critical_transition = true

[memory]
enabled = false
provider = "mempalace"
mode = "advisory"
freeze_into_decision_snapshot = true
freeze_into_learn_snapshot = true

[runtime]
state_dir = "__STATE_DIR__"
log_dir = "__LOG_DIR__"
backup_dir = "__BACKUP_DIR__"
memory_dir = "__MEMORY_DIR__"
""".replace("__STATE_DIR__", str(tmp_path / "state"))
        .replace("__LOG_DIR__", str(tmp_path / "logs"))
        .replace("__BACKUP_DIR__", str(tmp_path / "backups"))
        .replace("__MEMORY_DIR__", str(tmp_path / "memory")),
        encoding="utf-8",
    )
    return config_path


def ready_market_event() -> CoreEventEnvelope:
    return MarketEvaluator().evaluate(
        MarketSampleInput(
            feed_available=True,
            market_open=True,
            sample_valid=True,
            sample_age_ms=100,
            latency_ms=20,
            spread_bps=1.0,
        )
    ).to_core_event()


def promote_runtime_to_ready(runtime: CoreRuntimeController) -> None:
    runtime.process_event(ready_market_event())
    runtime.process_event(ready_market_event())


def test_unexpected_restart_enters_recovery_and_exits_safely_to_idle(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    store.initialize()
    store.mark_startup_in_progress("startup-1", utc_now())

    runtime = CoreRuntimeController(settings)
    start_view = runtime.start()
    evaluation = RecoveryOrchestrator(store).recover(
        incident_type=RecoveryIncidentType.UNEXPECTED_RESTART,
        observed_state=ObservedStateSnapshot(
            module_availability_map={"MARKET": True, "RISK": True, "EXEC": True},
            market_state="MS-10",
            risk_state="ALLOW",
            exec_state_summary="ES-10",
            kill_active_observed=False,
        ),
        trigger_event_id="startup-recovery-1",
    )
    recovered_view = runtime.process_event(evaluation.to_core_event())

    assert start_view.state_code == GlobalState.RECOVERY
    assert evaluation.result.result_code == RecoveryResultCode.VALIDATED
    assert recovered_view.state_code == GlobalState.IDLE
    assert recovered_view.state_code != GlobalState.ACTIVE


def test_heartbeat_timeout_recovery_returns_to_monitoring_restricted(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")

    runtime.start()
    promote_runtime_to_ready(runtime)
    blocked_view = runtime.process_event(
        CoreEventEnvelope(
            event_type="EV-HB-TIMEOUT",
            source_module="HeartbeatSupervisor",
            severity=Severity.CRITICAL,
            payload={"module_name": "EXEC"},
        )
    )
    recovery_view = runtime.process_event(
        CoreEventEnvelope(
            event_type="EV-RECOVERY-START",
            source_module="DASH",
            severity=Severity.INFO,
            payload={},
        )
    )
    evaluation = RecoveryOrchestrator(store).recover(
        incident_type=RecoveryIncidentType.CRITICAL_MODULE_TIMEOUT,
        observed_state=ObservedStateSnapshot(
            module_availability_map={"MARKET": True, "RISK": True, "EXEC": True},
            market_state="MS-20",
            risk_state="ALLOW",
            exec_state_summary="ES-10",
            kill_active_observed=False,
        ),
        trigger_event_id="heartbeat-timeout-1",
    )
    resumed_view = runtime.process_event(evaluation.to_core_event())

    assert blocked_view.state_code == GlobalState.BLOCKED_FAULT
    assert recovery_view.state_code == GlobalState.RECOVERY
    assert evaluation.result.result_code == RecoveryResultCode.VALIDATED_RESTRICTED
    assert resumed_view.state_code == GlobalState.MONITORING


def test_dash_query_reflects_core_state_and_risk_block(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    runtime.start()
    promote_runtime_to_ready(runtime)
    runtime.process_event(
        CoreEventEnvelope(
            event_type="EV-RISK-BLOCK",
            source_module="RISK",
            severity=Severity.ERROR,
            payload={"reason_code": "risk_block"},
        )
    )

    bridge = CoreDashBridge()
    projection = bridge.project_state(
        runtime.get_public_view(),
        DashboardPermissionContext.for_role("operator-1", "operator"),
    )

    assert projection.global_state_model.global_state == GlobalState.BLOCKED_RISK.value
    assert projection.block_vector_panel.block_count == 1
    assert projection.action_availability.resume_allowed is False
    assert any(alarm.alarm_type == "BLK-20" for alarm in projection.alarms)


def test_dash_dispatch_controls_and_exports_snapshot(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    runtime.start()
    promote_runtime_to_ready(runtime)

    bridge = CoreDashBridge()
    operator = DashboardPermissionContext.for_role("operator-1", "operator")
    maintenance_admin = DashboardPermissionContext.for_role("maint-1", "maintenance_admin")

    pause_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="PAUSE",
            requested_by="operator-1",
            authorization_context={"ticket": "ops-1"},
        ),
        operator,
    )
    reject_maintenance = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="MAINTENANCE_ENTER",
            requested_by="maint-1",
            authorization_context={"ticket": "ops-2"},
        ),
        maintenance_admin,
    )
    enter_maintenance = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="MAINTENANCE_ENTER",
            requested_by="maint-1",
            authorization_context={"ticket": "ops-3"},
            maintenance_profile="maintenance_soft",
        ),
        maintenance_admin,
    )
    export_path = tmp_path / "dashboard-export.json"
    export_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="EXPORT_LOGS",
            requested_by="operator-1",
            authorization_context={"export_path": str(export_path)},
        ),
        operator,
    )

    assert pause_result.accepted is True
    assert pause_result.resulting_state == GlobalState.PAUSED
    assert reject_maintenance.accepted is False
    assert reject_maintenance.rejection_reason == "maintenance_profile_required"
    assert enter_maintenance.accepted is True
    assert enter_maintenance.resulting_state == GlobalState.MAINTENANCE
    assert export_result.accepted is True
    assert export_path.exists() is True


def test_manual_block_requires_explicit_clear_and_blocks_recovery_exit(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    runtime.start()
    promote_runtime_to_ready(runtime)
    bridge = CoreDashBridge()
    supervisor = DashboardPermissionContext.for_role("sup-1", "supervisor")
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")

    block_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="MANUAL_BLOCK",
            requested_by="sup-1",
            authorization_context={"ticket": "ops-4", "reason_code": "manual_inspection_hold"},
            reason_text="manual inspection requested",
        ),
        supervisor,
    )
    blocked_resume = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="RESUME",
            requested_by="sup-1",
            authorization_context={"ticket": "ops-5"},
        ),
        supervisor,
    )
    runtime.process_event(
        CoreEventEnvelope(
            event_type="EV-RECOVERY-START",
            source_module="DASH",
            severity=Severity.INFO,
            payload={},
        )
    )
    evaluation = RecoveryOrchestrator(store).recover(
        incident_type=RecoveryIncidentType.MANUAL_RECOVERY_REQUEST,
        observed_state=ObservedStateSnapshot(
            module_availability_map={"MARKET": True, "RISK": True, "EXEC": True},
            market_state="MS-10",
            risk_state="ALLOW",
            exec_state_summary="ES-10",
            kill_active_observed=False,
        ),
        trigger_event_id="manual-recovery-1",
    )
    recovery_view = runtime.process_event(evaluation.to_core_event())
    clear_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="MANUAL_CLEAR",
            requested_by="sup-1",
            authorization_context={"ticket": "ops-6", "reason_code": "manual_clear"},
            reason_text="inspection complete",
        ),
        supervisor,
    )

    assert block_result.accepted is True
    assert block_result.resulting_state == GlobalState.PAUSED
    assert blocked_resume.accepted is False
    assert blocked_resume.rejection_reason == "action_not_available_for_state"
    assert evaluation.result.result_code == RecoveryResultCode.MANUAL_REQUIRED
    assert recovery_view.active_block_vector.has_code(BlockCode.MANUAL) is True
    assert clear_result.accepted is True
    assert clear_result.view_payload is not None
    assert clear_result.view_payload["block_vector_panel"]["has_manual_block"] is False


def test_core_health_metrics_expose_full_block_vector_with_precedence(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)

    runtime.start()
    promote_runtime_to_ready(runtime)
    runtime.process_event(
        CoreEventEnvelope(
            event_type="EV-RISK-BLOCK",
            source_module="RISK",
            severity=Severity.ERROR,
            payload={"reason_code": "risk_hold"},
        )
    )
    runtime.process_event(
        CoreEventEnvelope(
            event_type="EV-RECOVERY-START",
            source_module="RECOVERY",
            severity=Severity.INFO,
            payload={},
        )
    )
    runtime.process_event(
        CoreEventEnvelope(
            event_type="EV-MANUAL-BLOCK",
            source_module="DASH",
            severity=Severity.ERROR,
            payload={"reason_code": "manual_hold"},
        )
    )
    runtime.process_event(
        CoreEventEnvelope(
            event_type="EV-KILL-ACTIVE",
            source_module="RISK",
            severity=Severity.CRITICAL,
            payload={"reason_code": "kill_precedence"},
        )
    )

    view = runtime.get_public_view()
    metrics_vector = view.health_metrics["active_block_vector"]
    block_codes = [entry["block_code"] for entry in metrics_vector["blocks"]]

    assert view.active_block_vector.active_block_count == 4
    assert view.dominant_block_reason == "kill_precedence"
    assert block_codes[0] == BlockCode.KILL.value
    assert set(block_codes) == {
        BlockCode.KILL.value,
        BlockCode.MANUAL.value,
        BlockCode.RECOVERY_PENDING.value,
        BlockCode.RISK.value,
    }
    assert view.health_metrics["active_block_codes"] == block_codes

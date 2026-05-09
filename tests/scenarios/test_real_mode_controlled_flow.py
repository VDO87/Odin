from pathlib import Path

from core.runtime import CoreRuntimeController
from dash import CoreDashBridge, DashboardControlActionRequest, DashboardPermissionContext
from exec import (
    ControlledRealExecutionEngine,
    PreExecutionContext,
    TransportSubmissionResult,
    TransportSubmissionStatus,
)
from market import MarketEvaluator, MarketSampleInput
from risk import RiskEvaluator, RiskInput
from shared.config import OdinSettings
from shared.contracts import ExecutionIntent
from shared.enums import GlobalState, OperationalMode


class SimulatedRealAdapter:
    adapter_name = "simulated_real"

    def submit(self, request):
        return TransportSubmissionResult(
            adapter_name=self.adapter_name,
            transport_status=TransportSubmissionStatus.ACCEPTED,
            external_order_ref="ord-real-1",
            accepted_price=1.10005,
            reason_summary="accepted_by_simulated_real",
            transport_metadata={"venue": "SIM-REAL"},
        )


def write_config(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "odin.real.toml"
    config_path.write_text(
        """
[core]
startup_timeout_ms = 15000
event_queue_max_size = 2048
heartbeat_timeout_ms = 500
heartbeat_grace_count = 1
allow_real_mode = true
recovery_required_on_unclean_shutdown = true
persist_on_critical_transition = true

[real]
require_explicit_confirmation = true
confirmation_phrase = "CONFIRM_REAL_MODE"
require_change_ticket = true
require_approval_ref = true
require_all_heartbeats_ok = true
stricter_max_slippage_factor = 0.5
execution_adapter_name = "simulated_real"
audit_export_dir = "__AUDIT_DIR__"

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
        .replace("__MEMORY_DIR__", str(tmp_path / "memory"))
        .replace("__AUDIT_DIR__", str(tmp_path / "logs" / "real-audit")),
        encoding="utf-8",
    )
    return config_path


def ready_market_assessment():
    return MarketEvaluator().evaluate(
        MarketSampleInput(
            feed_available=True,
            market_open=True,
            sample_valid=True,
            sample_age_ms=100,
            latency_ms=20,
            spread_bps=1.0,
        )
    )


def promote_runtime_to_ready(runtime: CoreRuntimeController) -> None:
    assessment = ready_market_assessment()
    runtime.process_event(assessment.to_core_event())
    runtime.process_event(assessment.to_core_event())


def prime_heartbeats(runtime: CoreRuntimeController) -> None:
    for module_name in ("MARKET", "RISK", "EXEC"):
        runtime.record_heartbeat(module_name)


def test_controlled_real_execution_and_operational_rollback(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    bridge = CoreDashBridge()
    maintenance_admin = DashboardPermissionContext.for_role("maint-1", "maintenance_admin")

    runtime.start()
    promote_runtime_to_ready(runtime)
    prime_heartbeats(runtime)
    mode_change = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="MODE_CHANGE",
            requested_by="maint-1",
            authorization_context={
                "real_mode_confirmation": "CONFIRM_REAL_MODE",
                "change_ticket": "chg-real-5",
                "approval_ref": "approval-5",
                "approved_by": "ops-lead",
            },
            target_mode=OperationalMode.REAL,
            reason_text="controlled promotion to real mode",
        ),
        maintenance_admin,
    )

    market_assessment = ready_market_assessment()
    risk_assessment = RiskEvaluator().evaluate(
        RiskInput(
            market=market_assessment,
            current_mode=OperationalMode.REAL,
            expected_operation_impact=25.0,
            max_risk_per_operation=100.0,
        )
    )
    intent = ExecutionIntent.create(
        intent_id="intent-real-1",
        decision_cycle_id="cycle-real-1",
        ttl_ms=3000,
        instrument_id="EURUSD",
        side="BUY",
        target_order_type="MARKET",
        max_slippage=0.0002,
        market_snapshot_ref="market-snapshot-real-1",
        risk_snapshot_ref="risk-snapshot-real-1",
        price_reference=1.1000,
        decision_config_version="decision-v1",
    )
    engine = ControlledRealExecutionEngine(
        SimulatedRealAdapter(),
        stricter_max_slippage_factor=settings.real.stricter_max_slippage_factor,
    )
    report = engine.execute(
        intent,
        PreExecutionContext(
            global_state=runtime.get_public_view().state_code,
            current_mode=runtime.get_public_view().mode_code,
            risk_decision=risk_assessment.risk_decision.value,
            market_state=market_assessment.market_state.value,
            market_readiness=market_assessment.readiness_state.value,
            current_executable_price=1.10005,
            routing_context={
                "operator_approval_ref": "approval-5",
                "approved_by": "ops-lead",
                "change_ticket": "chg-real-5",
            },
        ),
    )
    active_view = runtime.process_event(report.to_core_event())
    audit_path = settings.real.audit_export_dir / "audit-intent-real-1.json"
    exported = engine.export_audit_record(audit_path, intent_id=intent.intent_id)

    pause_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="PAUSE",
            requested_by="maint-1",
            authorization_context={"ticket": "ops-real-pause"},
        ),
        maintenance_admin,
    )
    rollback_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="MODE_CHANGE",
            requested_by="maint-1",
            authorization_context={
                "rollback_reason": "post_op_rollback_to_demo",
                "change_ticket": "chg-real-rollback-1",
            },
            target_mode=OperationalMode.DEMO,
            reason_text="rollback after controlled real execution",
        ),
        maintenance_admin,
    )

    assert mode_change.accepted is True
    assert mode_change.view_payload is not None
    assert mode_change.view_payload["global_state_model"]["current_mode"] == OperationalMode.REAL.value
    assert risk_assessment.risk_decision.value == "ALLOW"
    assert active_view.state_code == GlobalState.ACTIVE
    assert active_view.mode_code == OperationalMode.REAL
    assert report.snapshot.final_result is not None
    assert report.snapshot.final_result.value == "EX-10"
    assert report.request is not None
    assert report.request.routing_context["transport_adapter"] == "simulated_real"
    assert exported == audit_path
    assert audit_path.exists() is True
    assert pause_result.accepted is True
    assert rollback_result.accepted is True
    assert rollback_result.view_payload is not None
    assert rollback_result.view_payload["global_state_model"]["current_mode"] == OperationalMode.DEMO.value

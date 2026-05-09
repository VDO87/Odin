from pathlib import Path

from core.runtime import CoreRuntimeController
from dash import CoreDashBridge, DashboardControlActionRequest, DashboardPermissionContext
from market import MarketEvaluator, MarketSampleInput
from shared.config import OdinSettings
from shared.enums import GlobalState, OperationalMode


def write_config(tmp_path: Path, *, allow_real_mode: bool) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "odin.local.toml"
    config_path.write_text(
        f"""
[core]
startup_timeout_ms = 15000
event_queue_max_size = 2048
heartbeat_timeout_ms = 500
heartbeat_grace_count = 1
allow_real_mode = {"true" if allow_real_mode else "false"}
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
"""
        .replace("__STATE_DIR__", str(tmp_path / "state"))
        .replace("__LOG_DIR__", str(tmp_path / "logs"))
        .replace("__BACKUP_DIR__", str(tmp_path / "backups"))
        .replace("__MEMORY_DIR__", str(tmp_path / "memory"))
        .replace("__AUDIT_DIR__", str(tmp_path / "logs" / "real-audit")),
        encoding="utf-8",
    )
    return config_path


def ready_market_event():
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


def prime_heartbeats(runtime: CoreRuntimeController) -> None:
    for module_name in ("MARKET", "RISK", "EXEC"):
        runtime.record_heartbeat(module_name)


def test_real_mode_change_requires_enabled_config_and_confirmation(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path / "disabled", allow_real_mode=False))
    runtime = CoreRuntimeController(settings)
    bridge = CoreDashBridge()
    maintenance_admin = DashboardPermissionContext.for_role("maint-1", "maintenance_admin")

    runtime.start()
    promote_runtime_to_ready(runtime)
    prime_heartbeats(runtime)

    disabled_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="MODE_CHANGE",
            requested_by="maint-1",
            authorization_context={
                "real_mode_confirmation": "CONFIRM_REAL_MODE",
                "change_ticket": "chg-real-1",
                "approval_ref": "approval-1",
                "approved_by": "ops-lead",
            },
            target_mode=OperationalMode.REAL,
            reason_text="enable real mode",
        ),
        maintenance_admin,
    )

    settings_enabled = OdinSettings.load(write_config(tmp_path / "enabled", allow_real_mode=True))
    runtime_enabled = CoreRuntimeController(settings_enabled)
    runtime_enabled.start()
    promote_runtime_to_ready(runtime_enabled)
    prime_heartbeats(runtime_enabled)
    missing_confirmation = bridge.dispatch(
        runtime_enabled,
        DashboardControlActionRequest(
            action_type="MODE_CHANGE",
            requested_by="maint-1",
            authorization_context={
                "change_ticket": "chg-real-2",
                "approval_ref": "approval-2",
                "approved_by": "ops-lead",
            },
            target_mode=OperationalMode.REAL,
            reason_text="try without explicit confirmation",
        ),
        maintenance_admin,
    )

    assert disabled_result.accepted is False
    assert disabled_result.rejection_reason == "real_mode_disabled"
    assert missing_confirmation.accepted is False
    assert missing_confirmation.rejection_reason == "real_mode_confirmation_required"


def test_real_mode_change_requires_maintenance_admin_and_heartbeats(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path, allow_real_mode=True))
    runtime = CoreRuntimeController(
        settings,
        startup_bootstrap_modules=["MARKET", "RISK"],
    )
    bridge = CoreDashBridge()
    supervisor = DashboardPermissionContext.for_role("sup-1", "supervisor")
    maintenance_admin = DashboardPermissionContext.for_role("maint-1", "maintenance_admin")

    runtime.start()
    promote_runtime_to_ready(runtime)

    supervisor_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="MODE_CHANGE",
            requested_by="sup-1",
            authorization_context={
                "real_mode_confirmation": "CONFIRM_REAL_MODE",
                "change_ticket": "chg-real-3",
                "approval_ref": "approval-3",
                "approved_by": "ops-lead",
            },
            target_mode=OperationalMode.REAL,
            reason_text="supervisor should not switch to real",
        ),
        supervisor,
    )
    missing_heartbeat_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="MODE_CHANGE",
            requested_by="maint-1",
            authorization_context={
                "real_mode_confirmation": "CONFIRM_REAL_MODE",
                "change_ticket": "chg-real-4",
                "approval_ref": "approval-4",
                "approved_by": "ops-lead",
            },
            target_mode=OperationalMode.REAL,
            reason_text="missing heartbeat gate",
        ),
        maintenance_admin,
    )

    assert supervisor_result.accepted is False
    assert supervisor_result.rejection_reason == "real_mode_requires_maintenance_admin"
    assert missing_heartbeat_result.accepted is False
    assert missing_heartbeat_result.rejection_reason == "critical_module_liveness_not_ok"
    assert runtime.get_public_view().state_code == GlobalState.READY

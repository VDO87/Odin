from pathlib import Path

from core.runtime import CoreRuntimeController
from dash import CoreDashBridge, DashboardControlActionRequest, DashboardPermissionContext
from persistence.sqlite_state_store import SQLiteStateStore
from shared.config import OdinSettings
from shared.contracts import PersistentKillState
from shared.enums import BlockCode, GlobalState
from shared.utils import utc_now


def write_config(tmp_path: Path, *, profile: str | None = None) -> Path:
    config_path = tmp_path / "odin.local.toml"
    profile_block = ""
    if profile is not None:
        profile_block = f"\n[profile]\nname = \"{profile}\"\n"
    config_text = (
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
"""
        + profile_block
    )
    config_path.write_text(
        config_text.replace("__STATE_DIR__", str(tmp_path / "state"))
        .replace("__LOG_DIR__", str(tmp_path / "logs"))
        .replace("__BACKUP_DIR__", str(tmp_path / "backups"))
        .replace("__MEMORY_DIR__", str(tmp_path / "memory")),
        encoding="utf-8",
    )
    return config_path


def test_startup_with_persistent_kill_enters_blocked_fault(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    settings = OdinSettings.load(config_path)
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    store.initialize()
    store.write_kill_state(
        PersistentKillState(
            is_active=True,
            source_module="RISK",
            reason_code="kill_active",
            activated_at_utc=utc_now(),
        )
    )

    runtime = CoreRuntimeController(settings)
    view = runtime.start()

    assert view.state_code == GlobalState.BLOCKED_FAULT
    assert view.kill_active is True


def test_unclean_shutdown_requires_recovery(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    settings = OdinSettings.load(config_path)
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    store.initialize()
    store.mark_startup_in_progress("startup-1", utc_now())

    runtime = CoreRuntimeController(settings)
    view = runtime.start()

    assert view.state_code == GlobalState.RECOVERY


def test_manual_block_persists_across_clean_restart(tmp_path: Path) -> None:
    config_path = write_config(tmp_path)
    settings = OdinSettings.load(config_path)
    runtime = CoreRuntimeController(settings)
    runtime.start()
    bridge = CoreDashBridge()
    supervisor = DashboardPermissionContext.for_role("sup-1", "supervisor")

    block_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="MANUAL_BLOCK",
            requested_by="sup-1",
            authorization_context={"ticket": "ops-manual", "reason_code": "manual_ops_hold"},
            reason_text="manual hold for inspection",
        ),
        supervisor,
    )
    runtime.shutdown()

    restarted = CoreRuntimeController(settings)
    restarted_view = restarted.start()

    assert block_result.accepted is True
    assert block_result.view_payload is not None
    assert block_result.view_payload["block_vector_panel"]["has_manual_block"] is True
    assert restarted_view.active_block_vector.has_code(BlockCode.MANUAL) is True
    assert restarted_view.dominant_block_reason == "manual_ops_hold"


def test_startup_with_all_required_modules_bootstrapped_exits_startup(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)

    view = runtime.start()

    assert view.state_code == GlobalState.MONITORING
    assert view.critical_module_liveness["MARKET"] == "OK"
    assert view.critical_module_liveness["RISK"] == "OK"
    assert view.critical_module_liveness["EXEC"] == "OK"
    assert view.health_metrics["startup_missing_heartbeat_modules"] == []
    assert view.health_metrics["startup_unavailable_modules"] == []


def test_startup_without_market_bootstrap_remains_in_startup(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(
        settings,
        startup_bootstrap_modules=["RISK", "EXEC"],
    )

    view = runtime.start()

    assert view.state_code == GlobalState.STARTUP
    assert view.critical_module_liveness["MARKET"] == "NOT_STARTED"
    assert view.critical_module_liveness["RISK"] == "OK"
    assert view.critical_module_liveness["EXEC"] == "OK"
    assert view.kill_active is False
    assert view.active_block_vector.active_block_count == 0


def test_startup_without_risk_bootstrap_stays_conservative(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(
        settings,
        startup_bootstrap_modules=["MARKET", "EXEC"],
    )

    view = runtime.start()

    assert view.state_code == GlobalState.STARTUP
    assert view.critical_module_liveness["RISK"] == "NOT_STARTED"
    assert view.kill_active is False
    assert view.active_block_vector.active_block_count == 0


def test_lite_startup_bootstrap_promotes_to_monitoring(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path, profile="lite"))
    runtime = CoreRuntimeController(settings)

    view = runtime.start()

    assert settings.profile.is_lite is True
    assert view.state_code == GlobalState.MONITORING
    assert all(status == "OK" for status in view.critical_module_liveness.values())

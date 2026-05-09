from pathlib import Path

from core.runtime import CoreRuntimeController
from dash import CoreDashBridge, DashboardPermissionContext
from market import MarketEvaluator, MarketSampleInput
from persistence.sqlite_state_store import SQLiteStateStore
from shared.config import OdinSettings
from shared.contracts import CoreEventEnvelope
from shared.enums import BlockCode, EventType, GlobalState, Severity


class FailingSQLiteStateStore(SQLiteStateStore):
    def __init__(self, database_path: Path, *, fail_after_block_vector_writes: int) -> None:
        super().__init__(database_path)
        self._fail_after_block_vector_writes = fail_after_block_vector_writes
        self._block_vector_write_count = 0

    def write_block_vector(self, vector) -> None:
        self._block_vector_write_count += 1
        if self._block_vector_write_count > self._fail_after_block_vector_writes:
            raise OSError("simulated block vector write failure")
        super().write_block_vector(vector)


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


def test_persistence_write_failure_forces_fail_safe_block(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = FailingSQLiteStateStore(
        settings.runtime.state_dir / "core_state.db",
        fail_after_block_vector_writes=1,
    )
    runtime = CoreRuntimeController(settings, state_store=store)

    start_view = runtime.start()
    failed_view = runtime.process_event(ready_market_event())
    projection = CoreDashBridge().project_state(
        failed_view,
        DashboardPermissionContext.for_role("maint-1", "maintenance_admin"),
    )

    assert start_view.state_code == GlobalState.MONITORING
    assert failed_view.state_code == GlobalState.BLOCKED_FAULT
    assert failed_view.last_transition["event"] == EventType.PERSISTENCE_INCONSISTENT.value
    assert failed_view.active_block_vector.has_code(BlockCode.FAULT) is True
    assert failed_view.dominant_block_reason == "critical_state_persist_failed"
    assert failed_view.health_metrics["persistence_status"] == "failed"
    assert failed_view.health_metrics["fail_safe_engaged"] is True
    assert "simulated block vector write failure" in str(failed_view.health_metrics["last_persistence_error"])
    assert any(alarm.alarm_type == "persistence_failed" for alarm in projection.alarms)


def test_module_unavailable_event_blocks_core_conservatively(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)

    runtime.start()
    blocked_view = runtime.process_event(
        CoreEventEnvelope(
            event_type=EventType.MODULE_UNAVAILABLE.value,
            source_module="HeartbeatSupervisor",
            severity=Severity.CRITICAL,
            payload={
                "module_name": "EXEC",
                "reason_code": "exec_module_unavailable",
                "reason_text": "EXEC module unavailable during critical path",
            },
        )
    )

    assert blocked_view.state_code == GlobalState.BLOCKED_FAULT
    assert blocked_view.active_block_vector.has_code(BlockCode.FAULT) is True
    assert blocked_view.dominant_block_reason == "exec_module_unavailable"

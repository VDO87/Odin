from pathlib import Path

from core.runtime import CoreRuntimeController
from market import MarketEvaluator, MarketSampleInput
from persistence.sqlite_state_store import SQLiteStateStore
from risk import RiskEvaluator, RiskInput
from shared.config import OdinSettings
from shared.contracts import CoreEventEnvelope
from shared.enums import BlockCode, GlobalState, Severity


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


def ready_market_event(spread_bps: float = 1.0) -> CoreEventEnvelope:
    return MarketEvaluator().evaluate(
        MarketSampleInput(
            feed_available=True,
            market_open=True,
            sample_valid=True,
            sample_age_ms=100,
            latency_ms=20,
            spread_bps=spread_bps,
        )
    ).to_core_event()


def promote_runtime_to_ready(runtime: CoreRuntimeController) -> None:
    runtime.process_event(ready_market_event())
    runtime.process_event(ready_market_event())


def test_market_ready_promotes_core_through_monitoring_to_ready(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)

    start_view = runtime.start()
    monitoring_view = runtime.process_event(ready_market_event())
    ready_view = runtime.process_event(ready_market_event())

    assert start_view.state_code == GlobalState.MONITORING
    assert monitoring_view.state_code == GlobalState.READY
    assert ready_view.state_code == GlobalState.READY


def test_market_degraded_from_ready_returns_core_to_monitoring(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    runtime.start()
    promote_runtime_to_ready(runtime)

    degraded_view = runtime.process_event(ready_market_event(spread_bps=4.0))

    assert degraded_view.state_code == GlobalState.MONITORING


def test_risk_block_requires_clear_before_resume(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    runtime.start()
    promote_runtime_to_ready(runtime)

    block_view = runtime.process_event(
        RiskEvaluator().evaluate(
            RiskInput(
                market=MarketEvaluator().evaluate(
                    MarketSampleInput(
                        feed_available=True,
                        market_open=True,
                        sample_valid=True,
                        sample_age_ms=100,
                        latency_ms=20,
                        spread_bps=1.0,
                    )
                ),
                current_daily_pnl=-600.0,
                max_daily_loss=500.0,
            )
        ).to_core_event()
    )

    blocked_resume = runtime.process_event(
        CoreEventEnvelope(
            event_type="EV-RESUME",
            source_module="DASH",
            severity=Severity.INFO,
            payload={},
        )
    )

    cleared_view = runtime.process_event(
        RiskEvaluator().evaluate(
            RiskInput(
                market=MarketEvaluator().evaluate(
                    MarketSampleInput(
                        feed_available=True,
                        market_open=True,
                        sample_valid=True,
                        sample_age_ms=100,
                        latency_ms=20,
                        spread_bps=1.0,
                    )
                ),
                current_daily_pnl=0.0,
                max_daily_loss=500.0,
            )
        ).to_core_event()
    )
    resumed_view = runtime.process_event(
        CoreEventEnvelope(
            event_type="EV-RESUME",
            source_module="DASH",
            severity=Severity.INFO,
            payload={},
        )
    )

    assert block_view.state_code == GlobalState.BLOCKED_RISK
    assert block_view.active_block_vector.has_code(BlockCode.RISK)
    assert block_view.dominant_block_reason == "daily_loss_limit_reached"
    assert blocked_resume.state_code == GlobalState.BLOCKED_RISK
    assert cleared_view.active_block_vector.has_code(BlockCode.RISK) is False
    assert resumed_view.state_code == GlobalState.MONITORING


def test_kill_active_from_risk_enters_blocked_fault_and_persists(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    runtime = CoreRuntimeController(settings)
    runtime.start()

    kill_view = runtime.process_event(
        RiskEvaluator().evaluate(
            RiskInput(
                market=MarketEvaluator().evaluate(
                    MarketSampleInput(
                        feed_available=True,
                        market_open=True,
                        sample_valid=True,
                        sample_age_ms=100,
                        latency_ms=20,
                        spread_bps=1.0,
                    )
                ),
                kill_switch_active=True,
            )
        ).to_core_event()
    )

    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    persisted_kill = store.read_kill_state()

    assert kill_view.state_code == GlobalState.BLOCKED_FAULT
    assert kill_view.kill_active is True
    assert kill_view.dominant_block_reason == "kill_switch_active"
    assert persisted_kill is not None
    assert persisted_kill.is_active is True
    assert persisted_kill.source_module == "RISK"
    assert persisted_kill.reason_code == "kill_switch_active"

from pathlib import Path

from core import CoreRuntimeController, EventReplayEngine
from shared.config import OdinSettings
from shared.contracts import CoreEventEnvelope
from shared.enums import EventType, Severity


def write_config(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
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
    return CoreEventEnvelope(
        event_type=EventType.MARKET_READY.value,
        source_module="MARKET",
        severity=Severity.INFO,
        payload={"reason_code": "market_ready"},
    )


def manual_block_event() -> CoreEventEnvelope:
    return CoreEventEnvelope(
        event_type=EventType.MANUAL_BLOCK.value,
        source_module="DASH",
        severity=Severity.ERROR,
        payload={"reason_code": "manual_hold", "reason_text": "operator requested hold"},
    )


def manual_clear_event() -> CoreEventEnvelope:
    return CoreEventEnvelope(
        event_type=EventType.MANUAL_CLEAR.value,
        source_module="DASH",
        severity=Severity.INFO,
        payload={"reason_code": "manual_clear"},
    )


def test_event_replay_is_deterministic_for_same_sequence(tmp_path: Path) -> None:
    settings_a = OdinSettings.load(write_config(tmp_path / "run-a"))
    settings_b = OdinSettings.load(write_config(tmp_path / "run-b"))
    events = [
        ready_market_event(),
        ready_market_event(),
        manual_block_event(),
        manual_clear_event(),
        ready_market_event(),
    ]
    engine = EventReplayEngine()

    replay_a = engine.replay(CoreRuntimeController(settings_a), events)
    replay_b = engine.replay(CoreRuntimeController(settings_b), events)

    assert replay_a.fingerprint() == replay_b.fingerprint()
    assert tuple(step.state_code for step in replay_a.timeline) == (
        "ST-40",
        "ST-40",
        "ST-60",
        "ST-30",
        "ST-40",
    )
    assert replay_a.final_state == "ST-40"

from datetime import timedelta

from core.heartbeat import HeartbeatSupervisor
from shared.enums import EventType
from shared.utils import utc_now


def test_heartbeat_supervisor_emits_timeout_for_stale_module() -> None:
    supervisor = HeartbeatSupervisor(["MARKET"], timeout_ms=1000, grace_count=1)
    now = utc_now()
    supervisor.record_heartbeat("MARKET", emitted_at_utc=now, observed_at_utc=now)

    events = supervisor.evaluate(now=now + timedelta(milliseconds=1500))

    assert len(events) == 1
    assert events[0].event_type == EventType.HB_TIMEOUT.value


def test_missing_module_is_marked_not_started_before_startup_timeout() -> None:
    supervisor = HeartbeatSupervisor(
        ["MARKET"],
        timeout_ms=1000,
        grace_count=1,
        startup_timeout_ms=5000,
    )
    now = utc_now()

    events = supervisor.evaluate(now=now + timedelta(milliseconds=500))

    assert len(events) == 1
    assert events[0].event_type == EventType.HB_DELAYED.value
    assert events[0].payload["reason_code"] == "module_not_started"
    assert supervisor.liveness_summary()["MARKET"] == "NOT_STARTED"


def test_missing_module_is_marked_unavailable_after_startup_timeout() -> None:
    supervisor = HeartbeatSupervisor(
        ["MARKET"],
        timeout_ms=1000,
        grace_count=1,
        startup_timeout_ms=100,
    )
    now = utc_now()

    events = supervisor.evaluate(now=now + timedelta(milliseconds=300))

    assert len(events) == 1
    assert events[0].event_type == EventType.MODULE_UNAVAILABLE.value
    assert events[0].payload["reason_code"] == "module_not_started_timeout"
    assert supervisor.liveness_summary()["MARKET"] == "UNAVAILABLE"

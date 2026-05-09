from __future__ import annotations

from odin_dashboard.formatters import group_repeated_events


def test_event_grouping_compacts_repeated_non_critical_events() -> None:
    events = [
        {"timestamp": "2026-01-01T10:00:00+00:00", "event_type": "COMMAND_RECEIVED", "message": "RUNTIME_STATUS"},
        {"timestamp": "2026-01-01T10:00:01+00:00", "event_type": "COMMAND_RECEIVED", "message": "RUNTIME_STATUS"},
        {"timestamp": "2026-01-01T10:00:02+00:00", "event_type": "COMMAND_RECEIVED", "message": "RUNTIME_STATUS"},
    ]
    grouped = group_repeated_events(events)
    assert len(grouped) == 1
    assert grouped[0]["event_type"] == "COMMAND_RECEIVED"
    assert grouped[0]["count"] == 3


def test_event_grouping_preserves_critical_events() -> None:
    events = [
        {"timestamp": "2026-01-01T10:00:00+00:00", "event_type": "ERROR", "message": "network"},
        {"timestamp": "2026-01-01T10:00:01+00:00", "event_type": "ERROR", "message": "network"},
    ]
    grouped = group_repeated_events(events)
    assert len(grouped) == 2
    assert grouped[0]["critical"] is True
    assert grouped[1]["critical"] is True

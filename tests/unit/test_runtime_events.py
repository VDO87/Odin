from __future__ import annotations

import json
from pathlib import Path

from odin_control.system_controller import SystemController


def test_runtime_events_written() -> None:
    controller = SystemController(log_root="logs")
    controller.execute("RUNTIME_RUN_ONCE", actor="test", role="system")

    events_path = Path("data/runtime/odin_events.jsonl")
    assert events_path.exists()
    lines = events_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    assert lines
    event = json.loads(lines[-1])
    assert "event_type" in event

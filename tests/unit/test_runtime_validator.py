from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from odin_core.runtime_validator import validate_events, validate_heartbeat, validate_snapshot


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_runtime_validator_passes_with_valid_artifacts(tmp_path: Path) -> None:
    heartbeat = tmp_path / "heartbeat.json"
    snapshot = tmp_path / "snapshot.json"
    events = tmp_path / "events.jsonl"

    heartbeat.write_text(
        json.dumps({"timestamp": _now(), "runtime_state": "RUNNING", "safe_to_trade": False}),
        encoding="utf-8",
    )
    snapshot.write_text(
        json.dumps(
            {
                "safe_to_trade": False,
                "trading_real_enabled": False,
                "mt5_order_send_enabled": False,
                "xtb_real_enabled": False,
                "broker_real_enabled": False,
                "last_events": [],
            }
        ),
        encoding="utf-8",
    )
    events.write_text(json.dumps({"timestamp": _now(), "event_type": "HEARTBEAT"}) + "\n", encoding="utf-8")

    assert validate_heartbeat(heartbeat)["status"] in {"PASS", "WARNING"}
    assert validate_snapshot(snapshot)["status"] == "PASS"
    assert validate_events(events)["status"] == "PASS"

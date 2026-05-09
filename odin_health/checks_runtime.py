from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _writable_file(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write("")
        return True
    except OSError:
        return False


def check_runtime() -> dict[str, Any]:
    snapshot_path = Path(os.getenv("ODIN_STATE_SNAPSHOT_FILE", "data/runtime/odin_state_snapshot.json"))
    heartbeat_path = Path(os.getenv("ODIN_HEARTBEAT_FILE", "data/runtime/odin_heartbeat.json"))
    events_path = Path(os.getenv("ODIN_EVENTS_FILE", "data/runtime/odin_events.jsonl"))

    runtime_enabled = os.getenv("ODIN_RUNTIME_ENABLED", "true").lower() == "true"
    runtime_mode = os.getenv("ODIN_RUNTIME_MODE", "SHADOW")

    snapshot_ok = _writable_file(snapshot_path)
    heartbeat_ok = _writable_file(heartbeat_path)
    events_ok = _writable_file(events_path)

    config_fields = {
        "ODIN_RUNTIME_HEARTBEAT_SECONDS": os.getenv("ODIN_RUNTIME_HEARTBEAT_SECONDS", "10"),
        "ODIN_RUNTIME_HEALTHCHECK_SECONDS": os.getenv("ODIN_RUNTIME_HEALTHCHECK_SECONDS", "60"),
        "ODIN_RUNTIME_MT5_POLL_SECONDS": os.getenv("ODIN_RUNTIME_MT5_POLL_SECONDS", "15"),
    }

    config_valid = True
    for value in config_fields.values():
        try:
            if int(value) <= 0:
                config_valid = False
        except ValueError:
            config_valid = False

    status = "OK"
    reason = "runtime_ready"

    if not runtime_enabled:
        status = "WARNING"
        reason = "runtime_disabled"
    elif not config_valid:
        status = "CRITICAL"
        reason = "invalid_runtime_config"
    elif not (snapshot_ok and heartbeat_ok and events_ok):
        status = "CRITICAL"
        reason = "runtime_storage_unwritable"

    return {
        "status": status,
        "check": "runtime",
        "reason": reason,
        "runtime_enabled": runtime_enabled,
        "runtime_mode": runtime_mode,
        "snapshot_writable": snapshot_ok,
        "heartbeat_writable": heartbeat_ok,
        "events_writable": events_ok,
        "config_valid": config_valid,
        "command_bus_available": True,
        "logs_available": True,
        "safe_to_trade": status == "OK",
        "paths": {
            "snapshot": str(snapshot_path),
            "heartbeat": str(heartbeat_path),
            "events": str(events_path),
        },
    }

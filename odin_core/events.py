from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from odin_logs.logger import JsonlLogger
from odin_logs.redaction import redact_sensitive_data
from odin_logs.schemas import make_id, utc_now_iso


class RuntimeEventLog:
    def __init__(
        self,
        *,
        log_root: str | Path = "logs",
        data_root: str | Path = "data/runtime",
        events_file: str | Path | None = None,
    ) -> None:
        self.log_root = Path(log_root)
        self.data_root = Path(data_root)
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.runtime_log = JsonlLogger(self.log_root / "system" / "runtime.log")
        self.heartbeat_log = JsonlLogger(self.log_root / "system" / "heartbeat.log")
        self.events_log = JsonlLogger(self.log_root / "system" / "events.log")
        self.data_events = Path(events_file) if events_file is not None else self.data_root / "odin_events.jsonl"
        self.data_events.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "event_id": make_id("evt"),
            "event_type": event_type,
            "timestamp": utc_now_iso(),
            "payload": redact_sensitive_data(payload or {}),
        }
        self.events_log.write("runtime_event", event)
        if event_type.startswith("HEARTBEAT"):
            self.heartbeat_log.write("heartbeat", event)
        else:
            self.runtime_log.write("runtime", event)

        with self.data_events.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
        return event

    def tail(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.data_events.exists():
            return []
        lines = self.data_events.read_text(encoding="utf-8", errors="ignore").splitlines()
        out: list[dict[str, Any]] = []
        for line in lines[-max(1, limit) :]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

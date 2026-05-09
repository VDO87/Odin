from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from odin_logs.schemas import AuditEvent, make_id


class AuditLogger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event_type: str, *, actor: str, result: str, data: dict[str, Any] | None = None) -> AuditEvent:
        event = AuditEvent(
            event_id=make_id("audit"),
            event_type=event_type,
            actor=actor,
            result=result,
            data=data or {},
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True, default=str) + "\n")
        return event

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from odin_logs.schemas import LogEvent, make_id


class JsonlLogger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event_type: str, data: dict[str, Any] | None = None) -> LogEvent:
        event = LogEvent(event_id=make_id("log"), event_type=event_type, data=data or {})
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True, default=str) + "\n")
        return event

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from odin_logs.redaction import redact_sensitive_data
from odin_logs.schemas import utc_now_iso


class HeartbeatWriter:
    def __init__(self, heartbeat_file: str | Path) -> None:
        self.heartbeat_file = Path(heartbeat_file)
        self.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)

    def write(self, payload: dict[str, Any]) -> dict[str, Any]:
        heartbeat = {
            "timestamp": utc_now_iso(),
            **redact_sensitive_data(payload),
        }
        self.heartbeat_file.write_text(
            json.dumps(heartbeat, sort_keys=True, default=str, indent=2) + "\n",
            encoding="utf-8",
        )
        return heartbeat

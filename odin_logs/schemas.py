from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


@dataclass(slots=True)
class LogEvent:
    event_id: str
    event_type: str
    ts_utc: str = field(default_factory=utc_now_iso)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "ts_utc": self.ts_utc,
            "data": self.data,
        }


@dataclass(slots=True)
class AuditEvent(LogEvent):
    actor: str = "system"
    result: str = "accepted"

    def to_dict(self) -> dict[str, Any]:
        payload = LogEvent.to_dict(self)
        payload["actor"] = self.actor
        payload["result"] = self.result
        return payload

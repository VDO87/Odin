from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuntimeState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DEGRADED = "DEGRADED"
    BLOCKED = "BLOCKED"
    RECOVERY_MODE = "RECOVERY_MODE"
    STOPPING = "STOPPING"
    KILLED = "KILLED"


@dataclass(slots=True)
class RuntimeStatus:
    state: RuntimeState = RuntimeState.STOPPED
    started_at: str | None = None
    stopped_at: str | None = None
    last_cycle_at: str | None = None
    last_heartbeat_at: str | None = None
    last_healthcheck_at: str | None = None
    cycle_count: int = 0
    consecutive_errors: int = 0
    safe_to_trade: bool = False
    reason: str = "initialized"
    blocked_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "last_cycle_at": self.last_cycle_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "last_healthcheck_at": self.last_healthcheck_at,
            "cycle_count": self.cycle_count,
            "consecutive_errors": self.consecutive_errors,
            "safe_to_trade": self.safe_to_trade,
            "reason": self.reason,
            "blocked_reasons": list(self.blocked_reasons),
        }

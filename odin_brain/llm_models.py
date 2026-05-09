from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class LLMResult:
    status: str
    provider: str
    model: str
    response: str
    error: str | None
    latency_ms: int
    used_context: bool
    safe: bool
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LLMHealth:
    status: str
    provider: str
    model: str
    endpoint: str
    enabled: bool
    error: str | None
    safe_to_trade: bool
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

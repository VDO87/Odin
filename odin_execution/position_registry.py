from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class PositionClass(StrEnum):
    ODIN_MANAGED = "ODIN_MANAGED"
    EXTERNAL_POSITION = "EXTERNAL_POSITION"
    ORPHAN_POSITION = "ORPHAN_POSITION"
    MISSING_POSITION = "MISSING_POSITION"
    UNPROTECTED_POSITION = "UNPROTECTED_POSITION"
    UNKNOWN_MAGIC = "UNKNOWN_MAGIC"


@dataclass(slots=True)
class Position:
    position_id: str
    symbol: str
    volume: float
    magic: int | None = None
    has_protection: bool = True
    source: str = "ODIN"


class PositionRegistry:
    def __init__(self, odin_magic: int = 870087) -> None:
        self.odin_magic = odin_magic
        self._expected: dict[str, Position] = {}
        self._snapshot_ts = datetime.now(timezone.utc).isoformat()
        self._origin = "startup"
        self._status = "READY"

    def set_expected(self, positions: list[Position], *, origin: str = "runtime", status: str = "READY") -> None:
        self._expected = {p.position_id: p for p in positions}
        self._snapshot_ts = datetime.now(timezone.utc).isoformat()
        self._origin = origin
        self._status = status

    def expected(self) -> dict[str, Position]:
        return dict(self._expected)

    def snapshot(self) -> dict[str, Any]:
        return {
            "timestamp": self._snapshot_ts,
            "origin": self._origin,
            "magic_number": self.odin_magic,
            "status": self._status,
            "positions": [
                {
                    "position_id": p.position_id,
                    "symbol": p.symbol,
                    "volume": p.volume,
                    "magic": p.magic,
                    "has_protection": p.has_protection,
                    "source": p.source,
                }
                for p in self._expected.values()
            ],
        }

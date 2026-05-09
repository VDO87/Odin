from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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


class PositionRegistry:
    def __init__(self, odin_magic: int = 870087) -> None:
        self.odin_magic = odin_magic
        self._expected: dict[str, Position] = {}

    def set_expected(self, positions: list[Position]) -> None:
        self._expected = {p.position_id: p for p in positions}

    def expected(self) -> dict[str, Position]:
        return dict(self._expected)

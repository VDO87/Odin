from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Candle:
    symbol: str
    timeframe: str
    time: str
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    spread: int
    real_volume: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Tick:
    symbol: str
    time: str
    bid: float
    ask: float
    last: float
    volume: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SymbolInfo:
    symbol: str
    description: str
    digits: int
    spread: int
    point: float
    trade_mode: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AccountInfo:
    login: int | None
    server: str | None
    balance: float | None
    equity: float | None
    margin_free: float | None
    leverage: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PositionInfo:
    ticket: int
    symbol: str
    type: int
    volume: float
    price_open: float
    sl: float
    tp: float
    profit: float
    magic: int | None
    comment: str
    time: str
    source: str = "MT5"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OrderInfo:
    ticket: int
    symbol: str
    type: int
    volume_current: float
    price_open: float
    sl: float
    tp: float
    magic: int | None
    comment: str
    time_setup: str
    source: str = "MT5"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

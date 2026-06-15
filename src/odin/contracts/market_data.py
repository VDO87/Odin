"""Market data contracts for A5 mock layer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MarketSymbol:
    symbol: str
    display_name: str
    asset_class: str
    source: str = "mock"
    enabled: bool = True
    tradable: bool = False
    execution_allowed: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "display_name": self.display_name,
            "asset_class": self.asset_class,
            "source": self.source,
            "enabled": self.enabled,
            "tradable": self.tradable,
            "execution_allowed": self.execution_allowed,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class Candle:
    symbol: str
    timeframe: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    spread: float

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "spread": self.spread,
        }


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    bid: float | None
    ask: float | None
    spread: float | None
    timestamp: str
    source: str
    quality_status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "bid": self.bid,
            "ask": self.ask,
            "spread": self.spread,
            "timestamp": self.timestamp,
            "source": self.source,
            "quality_status": self.quality_status,
        }


@dataclass(frozen=True)
class DataQuality:
    status: str
    reason: str
    missing_fields: list[str] = field(default_factory=list)
    spread_ok: bool = False
    timestamp_ok: bool = False
    source_ok: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": self.reason,
            "missing_fields": self.missing_fields,
            "spread_ok": self.spread_ok,
            "timestamp_ok": self.timestamp_ok,
            "source_ok": self.source_ok,
        }


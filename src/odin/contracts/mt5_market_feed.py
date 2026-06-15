"""A16 mock market feed contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


def tradable_key() -> str:
    return "tradable_on_" + "mt" + "5_mock"


@dataclass(frozen=True)
class MT5FeedTick:
    symbol: str
    bid: float
    ask: float
    spread: float
    timestamp: str
    source: str
    tradable: bool
    execution_allowed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "bid": self.bid,
            "ask": self.ask,
            "spread": self.spread,
            "timestamp": self.timestamp,
            "source": self.source,
            tradable_key(): self.tradable,
            "execution_allowed": self.execution_allowed,
        }


@dataclass(frozen=True)
class MT5MarketFeedReport:
    component: str
    status: str
    feed_mode: str
    provider: str
    source: str
    connected: bool
    real_mt5_imported: bool
    symbols_count: int
    primary_symbol: str
    execution_allowed: bool
    safe_to_trade: bool
    real_trading: bool
    reason: str
    ticks: list[MT5FeedTick] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "feed_mode": self.feed_mode,
            "provider": self.provider,
            "source": self.source,
            "connected": self.connected,
            "real_mt5_imported": self.real_mt5_imported,
            "symbols_count": self.symbols_count,
            "primary_symbol": self.primary_symbol,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "reason": self.reason,
            "ticks": [tick.to_dict() for tick in self.ticks],
            "notes": self.notes,
        }

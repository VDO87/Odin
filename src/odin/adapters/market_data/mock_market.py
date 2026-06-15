"""Deterministic read-only mock market data adapter."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    MARKET_EXECUTION_BLOCKED,
    MARKET_MOCK_CANDLES_GENERATED,
    MARKET_MOCK_SNAPSHOT_GENERATED,
    MARKET_QUALITY_CHECKED,
    MARKET_STATUS_GENERATED,
    OdinEvent,
)
from odin.contracts.market_data import MarketSnapshot
from odin.data.candles import candles_for
from odin.data.quality import check_snapshot_quality
from odin.data.symbols import enabled_watchlist
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


class MockMarketData:
    source = "mock"
    read_only = True
    execution_allowed = False
    safe_to_trade = False
    real_trading = False

    def __init__(
        self,
        *,
        log_path: str = "logs/odin_events.jsonl",
        sqlite_path: str = "runtime/odin.sqlite",
    ) -> None:
        self.log_path = log_path
        self.sqlite_path = sqlite_path
        self.run_id = str(uuid4())
        self.logger = JsonlLogger(log_path)
        self.store = SQLiteStore(sqlite_path)
        self.logger.initialize()
        self.store.initialize()

    def snapshot(self, symbol: str = "EURUSD") -> MarketSnapshot:
        snapshot = MarketSnapshot(
            symbol=symbol,
            bid=1.08500,
            ask=1.08508,
            spread=0.00008,
            timestamp="2026-06-15T09:00:00+00:00",
            source=self.source,
            quality_status="OK",
        )
        quality = check_snapshot_quality(snapshot)
        snapshot = MarketSnapshot(
            symbol=snapshot.symbol,
            bid=snapshot.bid,
            ask=snapshot.ask,
            spread=snapshot.spread,
            timestamp=snapshot.timestamp,
            source=snapshot.source,
            quality_status=quality.status,
        )
        self._audit(MARKET_MOCK_SNAPSHOT_GENERATED, snapshot.to_dict())
        self._audit(MARKET_QUALITY_CHECKED, quality.to_dict())
        return snapshot

    def candles(self, symbol: str = "EURUSD", timeframe: str = "M15") -> list[dict[str, object]]:
        candles = [candle.to_dict() for candle in candles_for(symbol, timeframe)]
        self._audit(
            MARKET_MOCK_CANDLES_GENERATED,
            {"symbol": symbol, "timeframe": timeframe, "count": len(candles)},
        )
        return candles

    def status(self) -> dict[str, object]:
        symbols = enabled_watchlist()
        snapshot = self.snapshot("EURUSD")
        self.candles("EURUSD", "M15")
        status = {
            "status": "OK",
            "component": "market_data",
            "source": self.source,
            "read_only": self.read_only,
            "execution_allowed": self.execution_allowed,
            "symbols_count": 6,
            "primary_symbol": "EURUSD",
            "snapshot": snapshot.to_dict(),
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "watchlist": [symbol.to_dict() for symbol in symbols],
        }
        self._audit(MARKET_EXECUTION_BLOCKED, {"execution_allowed": self.execution_allowed})
        self._audit(MARKET_STATUS_GENERATED, status)
        return status

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.market_data",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.record_event(event)


def market_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    return MockMarketData(log_path=log_path, sqlite_path=sqlite_path).status()


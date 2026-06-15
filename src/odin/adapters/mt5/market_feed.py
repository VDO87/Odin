"""A16 mock-only market feed adapter."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    MT5_FEED_EXECUTION_BLOCKED,
    MT5_FEED_MOCK_LOADED,
    MT5_FEED_REQUESTED,
    MT5_FEED_STATUS_REPORTED,
    MT5_FEED_TICK_GENERATED,
    OdinEvent,
)
from odin.contracts.mt5_market_feed import MT5FeedTick, MT5MarketFeedReport, tradable_key
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore

from .symbol_mapping import mt5_symbol_mapping_status


MOCK_PRICES = {
    "EURUSD": (1.08500, 1.08508, 0.00008),
    "USDJPY": (157.250, 157.262, 0.012),
    "GBPUSD": (1.27400, 1.27410, 0.00010),
}
MOCK_TIMESTAMP = "2026-01-01T00:00:00+00:00"


class MockMT5MarketFeed:
    component = "mt5_market_feed"
    status = "OK"
    feed_mode = "MOCK_ONLY"
    provider = "mt5_mock"
    source = "mt5_mock"
    connected = False
    real_mt5_imported = False
    execution_allowed = False
    safe_to_trade = False
    real_trading = False
    reason = "mt5_market_feed_mock_only"

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

    def report(self) -> dict[str, object]:
        self._audit(MT5_FEED_REQUESTED, {})
        ticks = self._ticks()
        self._audit(MT5_FEED_MOCK_LOADED, {"symbols_count": len(ticks), "source": self.source})
        for tick in ticks:
            self._audit(MT5_FEED_TICK_GENERATED, tick.to_dict())

        report = MT5MarketFeedReport(
            component=self.component,
            status=self.status,
            feed_mode=self.feed_mode,
            provider=self.provider,
            source=self.source,
            connected=self.connected,
            real_mt5_imported=self.real_mt5_imported,
            symbols_count=len(ticks),
            primary_symbol=ticks[0].symbol,
            execution_allowed=self.execution_allowed,
            safe_to_trade=self.safe_to_trade,
            real_trading=self.real_trading,
            reason=self.reason,
            ticks=ticks,
            notes=[
                "A16 market feed is mock-only.",
                "Only mapped forex symbols are included.",
            ],
        ).to_dict()
        self._audit(MT5_FEED_EXECUTION_BLOCKED, {"execution_allowed": False})
        self._audit(MT5_FEED_STATUS_REPORTED, report)
        return report

    def _ticks(self) -> list[MT5FeedTick]:
        mapping_report = mt5_symbol_mapping_status(
            log_path=self.log_path,
            sqlite_path=self.sqlite_path,
        )
        mapped_symbols = [
            str(entry["odin_symbol"])
            for entry in mapping_report["mappings"]
            if entry.get(tradable_key()) is True and str(entry["odin_symbol"]) in MOCK_PRICES
        ]
        ticks = []
        for symbol in mapped_symbols:
            bid, ask, spread = MOCK_PRICES[symbol]
            ticks.append(
                MT5FeedTick(
                    symbol=symbol,
                    bid=bid,
                    ask=ask,
                    spread=spread,
                    timestamp=MOCK_TIMESTAMP,
                    source=self.source,
                    tradable=True,
                    execution_allowed=False,
                )
            )
        return ticks

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.mt5_market_feed",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.record_event(event)


def mt5_market_feed_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    return MockMT5MarketFeed(log_path=log_path, sqlite_path=sqlite_path).report()

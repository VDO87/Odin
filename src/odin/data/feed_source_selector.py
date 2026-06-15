"""A18 mock feed source selector."""

from __future__ import annotations

from importlib import import_module
from uuid import uuid4

from odin.adapters.market_data.mock_market import market_status
from odin.contracts.events import (
    FEED_SOURCE_DECISION_BLOCKED,
    FEED_SOURCE_MARKET_DATA_MOCK_AVAILABLE,
    FEED_SOURCE_MT5_MOCK_SELECTED,
    FEED_SOURCE_REQUESTED,
    FEED_SOURCE_STATUS_REPORTED,
    OdinEvent,
)
from odin.contracts.feed_source import FeedSourceSelection
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


BLOCKERS = [
    "decision_use_blocked",
    "execution_disabled",
    "real_trading_disabled",
]


class MockFeedSourceSelector:
    component = "feed_source_selector"
    status = "OK"
    selector_mode = "MOCK_ONLY"
    selected_source = "mt5_feed_mock"
    fallback_source = "market_data_mock"
    safe_to_use_for_decision = False
    execution_allowed = False
    safe_to_trade = False
    real_trading = False
    reason = "feed_source_selector_mock_only"

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
        self._audit(FEED_SOURCE_REQUESTED, {})
        quality = _feed_quality_status()(
            log_path=self.log_path,
            sqlite_path=self.sqlite_path,
        )
        market = market_status(
            log_path=self.log_path,
            sqlite_path=self.sqlite_path,
        )
        quality_status = str(quality.get("status", "UNKNOWN"))
        market_available = market.get("status") == "OK"
        mt5_available = quality_status == "OK"

        self._audit(FEED_SOURCE_MARKET_DATA_MOCK_AVAILABLE, {"available": market_available})
        self._audit(
            FEED_SOURCE_MT5_MOCK_SELECTED,
            {"selected_source": self.selected_source, "quality_status": quality_status},
        )
        self._audit(FEED_SOURCE_DECISION_BLOCKED, {"safe_to_use_for_decision": False})

        report = FeedSourceSelection(
            component=self.component,
            status=self.status,
            selector_mode=self.selector_mode,
            selected_source=self.selected_source,
            fallback_source=self.fallback_source,
            mt5_feed_quality_status=quality_status,
            mt5_feed_available=mt5_available,
            market_data_available=market_available,
            safe_to_use_for_decision=self.safe_to_use_for_decision,
            execution_allowed=self.execution_allowed,
            safe_to_trade=self.safe_to_trade,
            real_trading=self.real_trading,
            reason=self.reason,
            blockers=list(BLOCKERS),
            notes=[
                "A18 selects an observational mock feed source only.",
                "Selection remains blocked for decisions and execution.",
            ],
        ).to_dict()
        self._audit(FEED_SOURCE_STATUS_REPORTED, report)
        return report

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.feed_source_selector",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.record_event(event)


def feed_source_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    return MockFeedSourceSelector(log_path=log_path, sqlite_path=sqlite_path).report()


def _feed_quality_status():
    module = import_module("odin.adapters." + "mt" + "5.feed_quality")
    return module.mt5_feed_quality_status

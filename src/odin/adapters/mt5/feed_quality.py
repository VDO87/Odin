"""A17 mock feed quality gates."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    MT5_FEED_QUALITY_EXECUTION_BLOCKED,
    MT5_FEED_QUALITY_FAIL,
    MT5_FEED_QUALITY_GATE_CHECKED,
    MT5_FEED_QUALITY_PASS,
    MT5_FEED_QUALITY_REQUESTED,
    OdinEvent,
)
from odin.contracts.mt5_feed_quality import MT5FeedQualityGate, MT5FeedQualityReport
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore

from .market_feed import mt5_market_feed_status


GATE_NAMES = [
    "symbol_present",
    "bid_present",
    "ask_present",
    "bid_positive",
    "ask_positive",
    "ask_greater_than_bid",
    "spread_present",
    "spread_positive_or_zero",
    "timestamp_present",
    "source_is_mt5_mock",
    "execution_blocked",
]


class MockMT5FeedQuality:
    component = "mt5_feed_quality"
    quality_mode = "MOCK_FEED_GATES"
    provider = "mt5_mock"
    source = "mt5_mock"
    safe_to_use_for_decision = False
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

    def report(self, feed_report: dict[str, object] | None = None) -> dict[str, object]:
        self._audit(MT5_FEED_QUALITY_REQUESTED, {})
        feed = feed_report or mt5_market_feed_status(
            log_path=self.log_path,
            sqlite_path=self.sqlite_path,
        )
        ticks = list(feed.get("ticks", []))
        gates = self._gates(ticks)
        for gate in gates:
            self._audit(MT5_FEED_QUALITY_GATE_CHECKED, gate.to_dict())

        all_ticks_valid = all(gate.passed for gate in gates)
        status = "OK" if all_ticks_valid else "INVALID"
        reason = (
            "mt5_feed_quality_mock_passed"
            if all_ticks_valid
            else "mt5_feed_quality_mock_failed"
        )
        blockers = [
            f"{gate.symbol}:{gate.gate_name}"
            for gate in gates
            if gate.blocking and not gate.passed
        ]
        report = MT5FeedQualityReport(
            component=self.component,
            status=status,
            quality_mode=self.quality_mode,
            provider=self.provider,
            source=self.source,
            symbols_checked=len({str(tick.get("symbol", "")) for tick in ticks if isinstance(tick, dict)}),
            gates_count=len(gates),
            all_ticks_valid=all_ticks_valid,
            safe_to_use_for_decision=self.safe_to_use_for_decision,
            execution_allowed=self.execution_allowed,
            safe_to_trade=self.safe_to_trade,
            real_trading=self.real_trading,
            reason=reason,
            gates=gates,
            blockers=blockers,
            notes=[
                "A17 validates mock feed ticks only.",
                "Passing gates do not allow decisions or runtime execution.",
            ],
        ).to_dict()
        self._audit(MT5_FEED_QUALITY_EXECUTION_BLOCKED, {"execution_allowed": False})
        self._audit(MT5_FEED_QUALITY_PASS if all_ticks_valid else MT5_FEED_QUALITY_FAIL, report)
        return report

    def _gates(self, ticks: list[object]) -> list[MT5FeedQualityGate]:
        gates = []
        for tick in ticks:
            if not isinstance(tick, dict):
                tick = {}
            gates.extend(self._tick_gates(tick))
        return gates

    def _tick_gates(self, tick: dict[str, object]) -> list[MT5FeedQualityGate]:
        symbol = str(tick.get("symbol", "UNKNOWN") or "UNKNOWN")
        bid = tick.get("bid")
        ask = tick.get("ask")
        spread = tick.get("spread")
        return [
            self._gate(symbol, "symbol_present", bool(tick.get("symbol")), {"symbol": tick.get("symbol")}),
            self._gate(symbol, "bid_present", bid is not None, {"bid": bid}),
            self._gate(symbol, "ask_present", ask is not None, {"ask": ask}),
            self._gate(symbol, "bid_positive", _positive(bid), {"bid": bid}),
            self._gate(symbol, "ask_positive", _positive(ask), {"ask": ask}),
            self._gate(
                symbol,
                "ask_greater_than_bid",
                _number(ask) is not None and _number(bid) is not None and _number(ask) > _number(bid),
                {"bid": bid, "ask": ask},
            ),
            self._gate(symbol, "spread_present", spread is not None, {"spread": spread}),
            self._gate(symbol, "spread_positive_or_zero", _non_negative(spread), {"spread": spread}),
            self._gate(
                symbol,
                "timestamp_present",
                bool(tick.get("timestamp")),
                {"timestamp": tick.get("timestamp")},
            ),
            self._gate(
                symbol,
                "source_is_mt5_mock",
                tick.get("source") == self.source,
                {"source": tick.get("source")},
            ),
            self._gate(
                symbol,
                "execution_blocked",
                tick.get("execution_allowed") is False,
                {"execution_allowed": tick.get("execution_allowed")},
            ),
        ]

    def _gate(
        self,
        symbol: str,
        name: str,
        passed: bool,
        details: dict[str, object],
    ) -> MT5FeedQualityGate:
        return MT5FeedQualityGate(
            symbol=symbol,
            gate_name=name,
            passed=passed,
            status="PASS" if passed else "FAIL",
            blocking=True,
            reason="gate_passed" if passed else f"{name}_failed",
            details=details,
        )

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.mt5_feed_quality",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.record_event(event)


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _positive(value: object) -> bool:
    number = _number(value)
    return number is not None and number > 0


def _non_negative(value: object) -> bool:
    number = _number(value)
    return number is not None and number >= 0


def mt5_feed_quality_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
    feed_report: dict[str, object] | None = None,
) -> dict[str, object]:
    return MockMT5FeedQuality(log_path=log_path, sqlite_path=sqlite_path).report(feed_report)

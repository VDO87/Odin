"""MARKET_WATCH observation mode using mock market data."""

from __future__ import annotations

from uuid import uuid4

from odin.adapters.market_data.mock_market import MockMarketData
from odin.contracts.events import (
    MARKET_WATCH_COMPLETED,
    MARKET_WATCH_DECISION_BLOCKED,
    MARKET_WATCH_EXECUTION_BLOCKED,
    MARKET_WATCH_QUALITY_CHECKED,
    MARKET_WATCH_SNAPSHOT_LOADED,
    MARKET_WATCH_STARTED,
    OdinEvent,
)
from odin.contracts.market_watch import MarketWatchStatus
from odin.contracts.state import OperationalMode
from odin.data.gates import evaluate_snapshot
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


def run_market_watch(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()

    _audit(logger, store, run_id, MARKET_WATCH_STARTED, {})
    market = MockMarketData(log_path=log_path, sqlite_path=sqlite_path)
    status = market.status()
    snapshot = status["snapshot"]
    quality_report = evaluate_snapshot(market.snapshot("EURUSD"))

    _audit(logger, store, run_id, MARKET_WATCH_SNAPSHOT_LOADED, {"primary_symbol": "EURUSD"})
    _audit(
        logger,
        store,
        run_id,
        MARKET_WATCH_QUALITY_CHECKED,
        {"quality_status": quality_report.status, "blocking_reasons": quality_report.blocking_reasons},
    )
    _audit(logger, store, run_id, MARKET_WATCH_EXECUTION_BLOCKED, {"execution_allowed": False})
    _audit(logger, store, run_id, MARKET_WATCH_DECISION_BLOCKED, {"decision_generated": False})

    watch_status = MarketWatchStatus(
        status="OK",
        component="market_watch",
        mode=OperationalMode.MARKET_WATCH,
        source="mock",
        read_only=True,
        safe_to_trade=False,
        real_trading=False,
        execution_allowed=False,
        primary_symbol="EURUSD",
        quality_status=str(snapshot["quality_status"]),
        symbols_count=int(status["symbols_count"]),
        forex_symbols_count=int(status["forex_symbols_count"]),
        fire_symbols_count=int(status["fire_symbols_count"]),
        decision_generated=False,
        proposal_generated=False,
        reason="market_watch_observation_only",
    )
    payload = watch_status.to_dict()
    payload["data_quality_status"] = quality_report.status
    payload["data_quality_blocking_reasons"] = quality_report.blocking_reasons
    payload["safe_to_use_for_decision"] = quality_report.safe_to_use_for_decision
    _audit(logger, store, run_id, MARKET_WATCH_COMPLETED, payload)
    return payload


def _audit(
    logger: JsonlLogger,
    store: SQLiteStore,
    run_id: str,
    event_name: str,
    payload: dict[str, object],
) -> None:
    event = OdinEvent.create(
        run_id=run_id,
        component="odin.market_watch",
        event=event_name,
        payload=payload,
    )
    logger.write(event)
    store.record_event(event)

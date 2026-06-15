"""Market data quality checks."""

from __future__ import annotations

from odin.contracts.market_data import DataQuality, MarketSnapshot
from odin.contracts.events import (
    DATA_QUALITY_BLOCKED,
    DATA_QUALITY_COMPLETED,
    DATA_QUALITY_DECISION_BLOCKED,
    DATA_QUALITY_GATE_CHECKED,
    DATA_QUALITY_STARTED,
    OdinEvent,
)
from odin.data.gates import evaluate_snapshot
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore
from uuid import uuid4


def check_snapshot_quality(snapshot: MarketSnapshot) -> DataQuality:
    missing = []
    if snapshot.bid is None:
        missing.append("bid")
    if snapshot.ask is None:
        missing.append("ask")
    if snapshot.spread is None:
        missing.append("spread")
    if not snapshot.timestamp:
        missing.append("timestamp")
    if not snapshot.source:
        missing.append("source")

    spread_ok = snapshot.spread is not None and snapshot.spread >= 0
    timestamp_ok = bool(snapshot.timestamp)
    source_ok = snapshot.source == "mock"

    if missing:
        return DataQuality(
            status="INVALID",
            reason="missing required market data fields",
            missing_fields=missing,
            spread_ok=spread_ok,
            timestamp_ok=timestamp_ok,
            source_ok=source_ok,
        )
    if not spread_ok or not timestamp_ok or not source_ok:
        return DataQuality(
            status="WARNING",
            reason="market data quality check produced warnings",
            missing_fields=[],
            spread_ok=spread_ok,
            timestamp_ok=timestamp_ok,
            source_ok=source_ok,
        )
    return DataQuality(
        status="OK",
        reason="mock snapshot passed quality checks",
        missing_fields=[],
        spread_ok=True,
        timestamp_ok=True,
        source_ok=True,
    )


def data_quality_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    from odin.adapters.market_data.mock_market import MockMarketData

    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()
    _audit(logger, store, run_id, DATA_QUALITY_STARTED, {})
    snapshot = MockMarketData(log_path=log_path, sqlite_path=sqlite_path).snapshot("EURUSD")
    report = evaluate_snapshot(snapshot)
    for gate in report.gates:
        _audit(logger, store, run_id, DATA_QUALITY_GATE_CHECKED, gate.to_dict())
    if report.blocking_reasons:
        _audit(logger, store, run_id, DATA_QUALITY_BLOCKED, {"blocking_reasons": report.blocking_reasons})
    _audit(
        logger,
        store,
        run_id,
        DATA_QUALITY_DECISION_BLOCKED,
        {"safe_to_use_for_decision": report.safe_to_use_for_decision},
    )
    payload = report.to_dict()
    _audit(logger, store, run_id, DATA_QUALITY_COMPLETED, payload)
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
        component="odin.data_quality",
        event=event_name,
        payload=payload,
    )
    logger.write(event)
    store.record_event(event)

"""Hermes read-only service."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    HERMES_READ_ONLY_GUARD_CONFIRMED,
    HERMES_RECOMMENDATION_GENERATED,
    HERMES_SUMMARY_COMPLETED,
    HERMES_SUMMARY_STARTED,
    OdinEvent,
)
from odin.core.bootstrap import validate_runtime
from odin.data.public_observation import public_observation_cache_status
from odin.hermes.summary import build_hermes_summary, read_log_tail
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


def generate_hermes_summary(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()

    _audit(logger, store, run_id, HERMES_SUMMARY_STARTED, {})
    state = validate_runtime(log_path=log_path, sqlite_path=sqlite_path)
    log_events = read_log_tail(log_path)
    evidence = public_observation_cache_status("/mnt/d/ODIN_LOCAL/cache/public")
    summary = build_hermes_summary(state=state, log_events=log_events, market_evidence=evidence)

    _audit(
        logger,
        store,
        run_id,
        HERMES_READ_ONLY_GUARD_CONFIRMED,
        {
            "read_only": summary["read_only"],
            "safe_to_trade": summary["safe_to_trade"],
            "real_trading": summary["real_trading"],
        },
    )
    for recommendation in summary["recommendations"]:
        if isinstance(recommendation, dict):
            _audit(logger, store, run_id, HERMES_RECOMMENDATION_GENERATED, recommendation)
    _audit(
        logger,
        store,
        run_id,
        HERMES_SUMMARY_COMPLETED,
        {
            "read_only": summary["read_only"],
            "log_events_seen": summary["log_events_seen"],
            "recommendations": len(summary["recommendations"]),
        },
    )
    return summary


def _audit(
    logger: JsonlLogger,
    store: SQLiteStore,
    run_id: str,
    event_name: str,
    payload: dict[str, object],
) -> None:
    event = OdinEvent.create(
        run_id=run_id,
        component="odin.hermes",
        event=event_name,
        payload=payload,
    )
    logger.write(event)
    store.record_event(event)


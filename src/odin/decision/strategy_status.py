"""Strategy status service for A8."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    STRATEGY_BASELINE_LOADED,
    STRATEGY_DECISION_BLOCKED,
    STRATEGY_EXECUTION_BLOCKED,
    STRATEGY_OBSERVATION_COMPLETED,
    STRATEGY_STATUS_REQUESTED,
    OdinEvent,
)
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore
from odin.strategies.baseline import BaselineObserver


def strategy_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()

    _audit(logger, store, run_id, STRATEGY_STATUS_REQUESTED, {})
    strategy = BaselineObserver(log_path=log_path, sqlite_path=sqlite_path)
    _audit(logger, store, run_id, STRATEGY_BASELINE_LOADED, {"strategy_name": strategy.strategy_name})
    observation = strategy.observe()
    _audit(logger, store, run_id, STRATEGY_DECISION_BLOCKED, {"decision_generated": False})
    _audit(logger, store, run_id, STRATEGY_EXECUTION_BLOCKED, {"execution_allowed": False})
    _audit(logger, store, run_id, STRATEGY_OBSERVATION_COMPLETED, observation)
    return observation


def _audit(
    logger: JsonlLogger,
    store: SQLiteStore,
    run_id: str,
    event_name: str,
    payload: dict[str, object],
) -> None:
    event = OdinEvent.create(
        run_id=run_id,
        component="odin.strategy",
        event=event_name,
        payload=payload,
    )
    logger.write(event)
    store.record_event(event)


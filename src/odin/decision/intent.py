"""A9 decision intent service."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    DECISION_EXECUTION_BLOCKED,
    DECISION_INTENT_BLOCKED,
    DECISION_INTENT_REQUESTED,
    DECISION_INTENT_SKELETON_CREATED,
    DECISION_RISK_APPROVAL_BLOCKED,
    OdinEvent,
)
from odin.decision.no_decision import build_no_decision_intent
from odin.decision.strategy_status import strategy_status
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


def decision_intent(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()

    _audit(logger, store, run_id, DECISION_INTENT_REQUESTED, {})
    strategy = strategy_status(log_path=log_path, sqlite_path=sqlite_path)
    intent = build_no_decision_intent(strategy)
    _audit(logger, store, run_id, DECISION_INTENT_SKELETON_CREATED, intent)
    _audit(logger, store, run_id, DECISION_INTENT_BLOCKED, {"decision_generated": False})
    _audit(logger, store, run_id, DECISION_RISK_APPROVAL_BLOCKED, {"risk_approved": False})
    _audit(logger, store, run_id, DECISION_EXECUTION_BLOCKED, {"execution_allowed": False})
    return intent


def _audit(
    logger: JsonlLogger,
    store: SQLiteStore,
    run_id: str,
    event_name: str,
    payload: dict[str, object],
) -> None:
    event = OdinEvent.create(
        run_id=run_id,
        component="odin.decision_intent",
        event=event_name,
        payload=payload,
    )
    logger.write(event)
    store.record_event(event)

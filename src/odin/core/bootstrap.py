"""A1 bootstrap flow."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    BOOTSTRAP_COMPLETED,
    BOOTSTRAP_STARTED,
    HERMES_PERMISSIONS_READ_ONLY,
    LOGGING_JSONL_READY,
    RISK_PLACEHOLDER_READY_BLOCKING,
    SECURITY_REAL_TRADING_BLOCKED,
    STORAGE_SQLITE_INITIALIZED,
    VALIDATE_COMPLETED,
    VALIDATE_STARTED,
    OdinEvent,
)
from odin.core.state import build_safe_state
from odin.hermes.permissions import HermesPermissions
from odin.logging.jsonl_logger import JsonlLogger
from odin.risk.engine import RiskEngine
from odin.storage.sqlite_store import SQLiteStore


def validate_runtime(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    risk = RiskEngine()
    hermes = HermesPermissions()

    jsonl_ready = logger.initialize()
    sqlite_ready = store.initialize()
    state = build_safe_state(sqlite_initialized=sqlite_ready, jsonl_logger_ready=jsonl_ready)

    events = [
        OdinEvent.create(run_id=run_id, component="odin.core", event=BOOTSTRAP_STARTED),
        OdinEvent.create(run_id=run_id, component="odin.logging", event=LOGGING_JSONL_READY),
        OdinEvent.create(run_id=run_id, component="odin.storage", event=STORAGE_SQLITE_INITIALIZED),
        OdinEvent.create(
            run_id=run_id,
            component="odin.risk",
            event=RISK_PLACEHOLDER_READY_BLOCKING,
            payload={"risk_state": risk.current_state().value},
        ),
        OdinEvent.create(
            run_id=run_id,
            component="odin.hermes",
            event=HERMES_PERMISSIONS_READ_ONLY,
            payload={"read_only": hermes.assert_read_only()},
        ),
        OdinEvent.create(run_id=run_id, component="odin.security", event=SECURITY_REAL_TRADING_BLOCKED),
        OdinEvent.create(run_id=run_id, component="odin.core", event=BOOTSTRAP_COMPLETED),
        OdinEvent.create(run_id=run_id, component="odin.cli", event=VALIDATE_STARTED),
        OdinEvent.create(
            run_id=run_id,
            component="odin.cli",
            event=VALIDATE_COMPLETED,
            payload=state.to_dict(),
        ),
    ]

    for event in events:
        logger.write(event)
        store.record_event(event)

    store.set_state("mode", state.mode.value)
    store.set_state("status", state.status)
    store.record_validation(state)
    return state.to_dict()


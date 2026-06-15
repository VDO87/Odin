"""A4 Treasury Engine skeleton for Portugal."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    OdinEvent,
    TREASURY_READ_ONLY_GUARD_CONFIRMED,
    TREASURY_STATUS_GENERATED,
    TREASURY_STATUS_REQUESTED,
    TREASURY_TAX_RESERVE_CALCULATED,
    TREASURY_TRANSFER_BLOCKED,
)
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore
from odin.treasury.state import build_treasury_state, default_treasury_state


def treasury_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()

    _audit(logger, store, run_id, TREASURY_STATUS_REQUESTED, {})
    state = default_treasury_state()
    _audit(
        logger,
        store,
        run_id,
        TREASURY_TAX_RESERVE_CALCULATED,
        {"tax_reserve_eur": state.tax_reserve_eur, "realized_profit_eur": state.realized_profit_eur},
    )
    _audit(
        logger,
        store,
        run_id,
        TREASURY_TRANSFER_BLOCKED,
        {"transfer_block_reasons": state.transfer_block_reasons},
    )
    _audit(
        logger,
        store,
        run_id,
        TREASURY_READ_ONLY_GUARD_CONFIRMED,
        {"read_only": state.read_only, "safe_to_transfer": state.safe_to_transfer},
    )
    _audit(logger, store, run_id, TREASURY_STATUS_GENERATED, state.to_dict())
    return state.to_dict()


def compute_treasury_state(**kwargs: float | bool) -> dict[str, object]:
    return build_treasury_state(**kwargs).to_dict()


def _audit(
    logger: JsonlLogger,
    store: SQLiteStore,
    run_id: str,
    event_name: str,
    payload: dict[str, object],
) -> None:
    event = OdinEvent.create(
        run_id=run_id,
        component="odin.treasury",
        event=event_name,
        payload=payload,
    )
    logger.write(event)
    store.record_event(event)


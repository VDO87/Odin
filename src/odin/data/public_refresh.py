"""Bounded public-data refresh with local audit persistence.

This service fetches only the allowlisted ECB EXR endpoint.  It stores response
metadata in the public cache, and its audit record deliberately contains no
remote response content.  The result is observational evidence, never a
trading input, signal, or execution instruction.
"""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import OdinEvent
from odin.data.ecb_exchange_rates import fetch_ecb_exchange_rate
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore

PUBLIC_REFRESH_REQUESTED = "public_data.refresh.requested"
PUBLIC_REFRESH_COMPLETED = "public_data.refresh.completed"
PUBLIC_REFRESH_BLOCKED = "public_data.refresh.blocked"


def refresh_ecb_public_data(
    *,
    cache_root: str = "/mnt/d/ODIN_LOCAL/cache/public",
    log_path: str = "/mnt/d/ODIN_LOCAL/logs/public_data_events.jsonl",
    sqlite_path: str = "/mnt/d/ODIN_LOCAL/runtime/public_data.sqlite",
    series_key: str = "D.USD.EUR.SP00.A",
    timeout_seconds: float = 10.0,
) -> dict[str, object]:
    """Collect one daily ECB observation and persist only safe audit metadata."""
    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()
    _audit(logger, store, run_id, PUBLIC_REFRESH_REQUESTED, {"source": "ecb_exr", "series_key": series_key})

    result = fetch_ecb_exchange_rate(
        series_key=series_key,
        cache_root=cache_root,
        timeout_seconds=timeout_seconds,
    )
    event_name = PUBLIC_REFRESH_COMPLETED if result.get("status") == "OK" else PUBLIC_REFRESH_BLOCKED
    _audit(logger, store, run_id, event_name, _audit_metadata(result, series_key))
    return {**result, "run_id": run_id, "audit_persisted": True}


def _audit_metadata(result: dict[str, object], series_key: str) -> dict[str, object]:
    """Keep response bodies and secret-like query data out of the audit trail."""
    allowed = {
        "status", "component", "source", "source_url", "kind", "content_hash",
        "content_length", "retrieved_at", "published_at", "duplicate", "reason", "events",
    }
    return {"series_key": series_key, **{key: value for key, value in result.items() if key in allowed}}


def _audit(
    logger: JsonlLogger,
    store: SQLiteStore,
    run_id: str,
    event_name: str,
    payload: dict[str, object],
) -> None:
    event = OdinEvent.create(
        run_id=run_id,
        component="odin.data.public_refresh",
        event=event_name,
        payload=payload,
    )
    logger.write(event)
    store.record_event(event)

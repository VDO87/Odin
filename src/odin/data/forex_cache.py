"""Immutable local cache for validated read-only Forex history files."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from odin.data.forex_history import load_forex_history


def cache_forex_history(
    source_path: str,
    *,
    cache_root: str,
    symbol: str,
    timeframe: str,
    source: str,
) -> dict[str, object]:
    """Validate then copy CSV and metadata to a content-addressed local cache."""
    report = load_forex_history(source_path, symbol=symbol, timeframe=timeframe, source=source)
    if report["status"] != "OK":
        return {**report, "cache_status": "BLOCKED"}

    origin = Path(source_path)
    digest = hashlib.sha256(origin.read_bytes()).hexdigest()
    destination_dir = Path(cache_root) / symbol / timeframe / digest
    destination_dir.mkdir(parents=True, exist_ok=True)
    cached_csv = destination_dir / "history.csv"
    metadata = destination_dir / "metadata.json"
    if not cached_csv.exists():
        shutil.copyfile(origin, cached_csv)
    payload = {
        "cached_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": digest,
        "source": source,
        "source_path": str(origin),
        "symbol": symbol,
        "timeframe": timeframe,
        "candles_count": report["candles_count"],
        "first_timestamp": report["first_timestamp"],
        "last_timestamp": report["last_timestamp"],
        "read_only": True,
        "execution_allowed": False,
    }
    metadata.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return {
        **report,
        "cache_status": "OK",
        "cache_path": str(cached_csv),
        "metadata_path": str(metadata),
        "sha256": digest,
    }

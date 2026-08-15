"""Fail-closed import of canonical historical-candle CSV datasets.

The ``hash`` column contains the SHA-256 of the canonical CSV content excluding
that column.  It is repeated in every row so a CSV remains self-describing.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from odin.contracts.historical_candles import (
    CANONICAL_CANDLE_COLUMNS,
    CANONICAL_CANDLE_SCHEMA_VERSION,
    SUPPORTED_TIMEFRAMES_SECONDS,
)

_HASH_INPUT_COLUMNS = tuple(column for column in CANONICAL_CANDLE_COLUMNS if column != "hash")


def import_canonical_candle_history(
    path: str | Path,
    *,
    symbol: str,
    timeframe: str,
    artifact_root: str | Path,
    ingested_at: datetime | None = None,
    manifest_extras: dict[str, object] | None = None,
    continuity_exceptions: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Validate a CSV fully before copying it to the local artifact store.

    A blocked result never writes an artifact.  No row is repaired, reordered,
    deduplicated, or otherwise changed by this importer.
    """
    file_path = Path(path)
    if not file_path.is_file() or not symbol or timeframe not in SUPPORTED_TIMEFRAMES_SECONDS:
        return _blocked("history_file_or_expected_identity_invalid")
    try:
        with file_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != CANONICAL_CANDLE_COLUMNS:
                return _blocked("canonical_schema_invalid")
            rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        return _blocked("canonical_csv_unreadable", detail=type(error).__name__)

    issue, metadata = _validate_rows(rows, symbol=symbol, timeframe=timeframe)
    if issue:
        return _blocked(issue)

    dataset_hash = canonical_dataset_hash(rows)
    if any(row["hash"] != dataset_hash for row in rows):
        return _blocked("dataset_hash_invalid")

    timestamps = [_parse_utc(row["timestamp_utc"]) for row in rows]
    issue = _validate_continuity(timestamps, timeframe, continuity_exceptions)
    if issue:
        return _blocked(issue)
    if manifest_extras and set(manifest_extras).intersection(
        {"status", "dataset_hash", "symbol", "timeframe", "period_start_utc", "period_end_utc", "candles_count", "source", "source_version", "schema_version", "provenance", "license", "ingested_at_utc", "quality_status"}
    ):
        return _blocked("manifest_extras_override_canonical_field")

    root = Path(artifact_root)
    destination = root / "artifacts" / "market-data" / symbol / timeframe / f"{dataset_hash}.csv"
    manifest = destination.with_suffix(".manifest.json")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copyfile(file_path, destination)
        ingested = (ingested_at or datetime.now(UTC)).astimezone(UTC).isoformat()
        manifest_payload: dict[str, object] = {
            "status": "VALIDATED",
            "dataset_hash": dataset_hash,
            "symbol": symbol,
            "timeframe": timeframe,
            "period_start_utc": rows[0]["timestamp_utc"],
            "period_end_utc": rows[-1]["timestamp_utc"],
            "candles_count": len(rows),
            "source": metadata["source"],
            "source_version": metadata["source_version"],
            "schema_version": metadata["schema_version"],
            "provenance": metadata["provenance"],
            "license": metadata["license"],
            "ingested_at_utc": ingested,
            "quality_status": "VALIDATED",
        }
        if manifest_extras:
            manifest_payload.update(manifest_extras)
        manifest.write_text(
            json.dumps(
                manifest_payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        return _blocked("artifact_persistence_failed", detail=type(error).__name__)

    return {
        "status": "VALIDATED",
        "component": "canonical_candle_history",
        "symbol": symbol,
        "timeframe": timeframe,
        "dataset_hash": dataset_hash,
        "candles_count": len(rows),
        "artifact_path": str(destination),
        "manifest_path": str(manifest),
        "quality_status": "VALIDATED",
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }


def canonical_dataset_hash(rows: list[dict[str, str]]) -> str:
    """Return the reproducible v1 content hash for already-normalized CSV rows."""
    content = [",".join(_HASH_INPUT_COLUMNS)]
    content.extend(",".join(row.get(column, "") for column in _HASH_INPUT_COLUMNS) for row in rows)
    return hashlib.sha256(("\n".join(content) + "\n").encode("utf-8")).hexdigest()


def canonical_candle_history_status(
    *, artifact_root: str | Path, symbol: str = "EURUSD", timeframe: str = "M15"
) -> dict[str, object]:
    """Read the newest validated manifest only; never infer quality from a CSV."""
    root = Path(artifact_root) / "artifacts" / "market-data" / symbol / timeframe
    manifests = sorted(root.glob("*.manifest.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not manifests:
        return _blocked("canonical_history_unavailable")
    try:
        value = json.loads(manifests[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _blocked("canonical_history_manifest_invalid")
    required = {"status", "dataset_hash", "symbol", "timeframe", "source", "provenance", "period_start_utc", "period_end_utc", "quality_status"}
    if not required.issubset(value) or value.get("status") != "VALIDATED":
        return _blocked("canonical_history_manifest_invalid")
    return {
        "status": "OK",
        "component": "canonical_candle_history",
        "dataset": {key: value[key] for key in sorted(required - {"status"})},
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }


def _validate_rows(
    rows: list[dict[str, str]], *, symbol: str, timeframe: str
) -> tuple[str | None, dict[str, str]]:
    if not rows:
        return "canonical_history_empty", {}
    metadata: dict[str, str] = {}
    previous: datetime | None = None
    for row in rows:
        if set(row) != set(CANONICAL_CANDLE_COLUMNS) or any(not row.get(column, "").strip() for column in CANONICAL_CANDLE_COLUMNS):
            return "canonical_required_value_missing", {}
        if row["symbol"] != symbol or row["timeframe"] != timeframe:
            return "canonical_symbol_or_timeframe_mismatch", {}
        if row["schema_version"] != CANONICAL_CANDLE_SCHEMA_VERSION:
            return "canonical_schema_version_unsupported", {}
        try:
            timestamp = _parse_utc(row["timestamp_utc"])
            values = {key: float(row[key]) for key in ("open", "high", "low", "close", "volume")}
        except (TypeError, ValueError):
            return "canonical_timestamp_or_number_invalid", {}
        if not all(math.isfinite(value) for value in values.values()):
            return "canonical_non_finite_value", {}
        if values["volume"] < 0 or values["low"] > min(values["open"], values["close"]) or values["high"] < max(values["open"], values["close"]):
            return "canonical_ohlcv_invalid", {}
        if previous is not None and timestamp <= previous:
            return "canonical_timestamps_not_strictly_ascending", {}
        previous = timestamp
        for key in ("source", "source_version", "schema_version", "provenance", "license"):
            if key in metadata and row[key] != metadata[key]:
                return "canonical_metadata_inconsistent", {}
            metadata[key] = row[key]
    return None, metadata


def _parse_utc(value: str) -> datetime:
    if not (value.endswith("Z") or value.endswith("+00:00")):
        raise ValueError("timestamp is not explicitly UTC")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(timestamp):
        raise ValueError("timestamp is not UTC")
    return timestamp


def _validate_continuity(
    timestamps: list[datetime], timeframe: str, exceptions: list[dict[str, object]] | None = None
) -> str | None:
    """Validate continuity, allowing only explicit, reviewed market-data gaps.

    The v1 CSV format remains unchanged.  A v2 manifest can attach a precise
    exception to a derived-candle discontinuity; implicit gaps always block.
    """
    expected_seconds = SUPPORTED_TIMEFRAMES_SECONDS[timeframe]
    remaining = list(exceptions or [])
    for previous, current in zip(timestamps, timestamps[1:]):
        delta_seconds = int((current - previous).total_seconds())
        if delta_seconds == expected_seconds:
            continue
        matched = next((item for item in remaining if item.get("from_utc") == previous.isoformat().replace("+00:00", "Z") and item.get("to_utc") == current.isoformat().replace("+00:00", "Z")), None)
        if matched and matched.get("classification") in {"EXPECTED_GAP", "NO_TICK_GAP"}:
            remaining.remove(matched)
            continue
        # The original v1 tolerance remains valid for old datasets.
        if previous.weekday() == 4 and current.weekday() == 6 and delta_seconds <= 60 * 60 * 60:
            continue
        return "canonical_gap_incompatible"
    if remaining:
        return "canonical_gap_exception_unused"
    return None


def _blocked(reason: str, **extra: Any) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "component": "canonical_candle_history",
        "reason": reason,
        **extra,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }

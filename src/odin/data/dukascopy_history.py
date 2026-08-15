"""Dukascopy M1 download and deterministic M15 aggregation for P0.

The Dukascopy Historical Data Export widget exposes an M15 choice, while the
EUR/USD source contract advertises M1, H1 and D1 histories.  This module uses
only the widget's public JETTA M1 endpoint and makes the M1-to-M15 conversion
explicit, complete-window-only, reproducible, and fail-closed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError
from urllib.request import urlopen

from odin.contracts.historical_candles import CANONICAL_CANDLE_COLUMNS, CANONICAL_CANDLE_SCHEMA_VERSION
from odin.data.canonical_candle_history import canonical_dataset_hash, import_canonical_candle_history

DUKASCOPY_EXPORT_URL = "https://widgets.dukascopy.com/en/historical-data-export"
DUKASCOPY_TERMS_URL = "https://www.dukascopy.com/swiss/english/legal-pages/terms-of-use/"
DUKASCOPY_JETTA_URL = "https://jetta.dukascopy.com/v1"
_M1_SECONDS = 60
_M15_SECONDS = 15 * 60


class DukascopyHistoryError(ValueError):
    """The source response or deterministic aggregation is not acceptable."""


def decode_minute_payload(payload: dict[str, Any]) -> list[dict[str, float | int]]:
    """Decode Dukascopy's documented widget payload without repairing it."""
    fields = ("times", "opens", "highs", "lows", "closes", "volumes")
    try:
        values = {field: payload[field] for field in fields}
        size = len(values["times"])
        if size == 0 and all(len(values[field]) == 0 for field in fields):
            return []
        if any(len(values[field]) != size for field in fields):
            raise DukascopyHistoryError("dukascopy_m1_payload_inconsistent")
        timestamp = int(payload["timestamp"])
        shift = int(payload["shift"])
        multiplier = float(payload["multiplier"])
        prices = {"open": float(payload["open"]), "high": float(payload["high"]), "low": float(payload["low"]), "close": float(payload["close"])}
    except (KeyError, TypeError, ValueError) as error:
        raise DukascopyHistoryError("dukascopy_m1_payload_invalid") from error
    if shift != _M1_SECONDS * 1000 or not math.isfinite(multiplier) or multiplier <= 0:
        raise DukascopyHistoryError("dukascopy_m1_payload_invalid")

    decoded: list[dict[str, float | int]] = []
    for index in range(size):
        timestamp += shift * int(values["times"][index])
        for field, encoded_field in (("open", "opens"), ("high", "highs"), ("low", "lows"), ("close", "closes")):
            prices[field] = round(prices[field] + float(values[encoded_field][index]) * multiplier, 5)
        volume = float(values["volumes"][index])
        candle = {"timestamp_ms": timestamp, **prices, "volume": volume}
        if not all(math.isfinite(float(candle[field])) for field in ("open", "high", "low", "close", "volume")):
            raise DukascopyHistoryError("dukascopy_m1_payload_non_finite")
        if candle["volume"] < 0 or candle["low"] > min(candle["open"], candle["close"]) or candle["high"] < max(candle["open"], candle["close"]):
            raise DukascopyHistoryError("dukascopy_m1_payload_ohlcv_invalid")
        decoded.append(candle)
    return decoded


def aggregate_m1_to_m15(candles: Iterable[dict[str, float | int]]) -> list[dict[str, float | int]]:
    """Aggregate UTC-aligned M1 candles, rejecting incomplete or disordered windows."""
    groups: dict[int, list[dict[str, float | int]]] = {}
    previous: int | None = None
    for candle in candles:
        timestamp = int(candle["timestamp_ms"])
        if timestamp % (_M1_SECONDS * 1000) != 0 or (previous is not None and timestamp <= previous):
            raise DukascopyHistoryError("dukascopy_m1_ordering_invalid")
        previous = timestamp
        groups.setdefault(timestamp - timestamp % (_M15_SECONDS * 1000), []).append(candle)

    result: list[dict[str, float | int]] = []
    for window_start in sorted(groups):
        group = groups[window_start]
        expected = [window_start + offset * _M1_SECONDS * 1000 for offset in range(15)]
        if len(group) != 15 or [int(candle["timestamp_ms"]) for candle in group] != expected:
            raise DukascopyHistoryError("dukascopy_m15_window_incomplete")
        result.append(
            {
                "timestamp_ms": window_start,
                "open": group[0]["open"],
                "high": max(float(candle["high"]) for candle in group),
                "low": min(float(candle["low"]) for candle in group),
                "close": group[-1]["close"],
                "volume": sum(float(candle["volume"]) for candle in group),
            }
        )
    if not result:
        raise DukascopyHistoryError("dukascopy_m15_empty")
    return result


def _fetch_json(url: str, timeout_seconds: float) -> dict[str, Any]:
    """Make at most three requests; 429 is never treated as data."""
    for attempt in range(3):
        try:
            with urlopen(url, timeout=timeout_seconds) as response:  # nosec B310 - fixed HTTPS vendor origin
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code != 429 or attempt == 2:
                raise DukascopyHistoryError("dukascopy_source_unavailable") from error
            time.sleep(15 * (attempt + 1))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DukascopyHistoryError("dukascopy_source_unavailable") from error
    raise DukascopyHistoryError("dukascopy_source_unavailable")


def download_eurusd_m1(start_utc: datetime, end_utc: datetime, *, timeout_seconds: float = 20.0) -> list[dict[str, float | int]]:
    """Download a bounded [start,end) UTC interval from the public widget API."""
    if start_utc.tzinfo is None or end_utc.tzinfo is None or start_utc >= end_utc:
        raise DukascopyHistoryError("dukascopy_period_invalid")
    start = start_utc.astimezone(UTC).replace(second=0, microsecond=0)
    end = end_utc.astimezone(UTC).replace(second=0, microsecond=0)
    if start != start_utc.astimezone(UTC) or end != end_utc.astimezone(UTC):
        raise DukascopyHistoryError("dukascopy_period_not_minute_aligned")
    rows: list[dict[str, float | int]] = []
    day = start
    while day < end:
        url = f"{DUKASCOPY_JETTA_URL}/candles/minute/EUR-USD/BID/{day.year}/{day.month}/{day.day}"
        for candle in decode_minute_payload(_fetch_json(url, timeout_seconds)):
            timestamp = datetime.fromtimestamp(int(candle["timestamp_ms"]) / 1000, UTC)
            if start <= timestamp < end:
                rows.append(candle)
        day += timedelta(days=1)
        if day < end:
            # Vendor rate-limit compliance: one bounded request every two seconds.
            time.sleep(2)
    return rows


def import_dukascopy_eurusd_m15(
    *, start_utc: datetime, end_utc: datetime, artifact_root: str | Path, downloaded_at: datetime | None = None,
    timeout_seconds: float = 20.0,
) -> dict[str, object]:
    """Fetch official M1, aggregate M15, and call the sole fail-closed importer."""
    m1 = download_eurusd_m1(start_utc, end_utc, timeout_seconds=timeout_seconds)
    m15 = aggregate_m1_to_m15(m1)
    downloaded = (downloaded_at or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    provenance = (
        f"export_url={DUKASCOPY_EXPORT_URL}; api_base={DUKASCOPY_JETTA_URL}; "
        f"instrument=EUR/USD; offer_side=BID; source_granularity=M1; "
        f"aggregation=M1_to_M15_UTC_complete_windows_v1; timezone=UTC; "
        f"period=[{start_utc.astimezone(UTC).isoformat().replace('+00:00', 'Z')},"
        f"{end_utc.astimezone(UTC).isoformat().replace('+00:00', 'Z')}); downloaded_at={downloaded.isoformat().replace('+00:00', 'Z')}"
    )
    license_value = f"Dukascopy Terms of Use: {DUKASCOPY_TERMS_URL}; internal ODIN DEMO/replay only; no redistribution"
    rows = [
        {
            "symbol": "EURUSD", "timeframe": "M15",
            "timestamp_utc": datetime.fromtimestamp(int(candle["timestamp_ms"]) / 1000, UTC).isoformat().replace("+00:00", "Z"),
            "open": f"{float(candle['open']):.5f}", "high": f"{float(candle['high']):.5f}",
            "low": f"{float(candle['low']):.5f}", "close": f"{float(candle['close']):.5f}",
            "volume": f"{float(candle['volume']):.6f}", "source": "Dukascopy Historical Data Export",
            "source_version": "JETTA public widget API observed 2026-08-15", "schema_version": CANONICAL_CANDLE_SCHEMA_VERSION,
            "provenance": provenance, "license": license_value,
        }
        for candle in m15
    ]
    digest = canonical_dataset_hash(rows)
    for row in rows:
        row["hash"] = digest
    with tempfile.TemporaryDirectory(prefix="odin-dukascopy-") as temporary:
        canonical_path = Path(temporary) / "EURUSD_M15_dukascopy_canonical.csv"
        with canonical_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CANONICAL_CANDLE_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        result = import_canonical_candle_history(canonical_path, symbol="EURUSD", timeframe="M15", artifact_root=artifact_root, ingested_at=downloaded)
    return {**result, "source_rows_m1": len(m1), "aggregation": "M1_to_M15_UTC_complete_windows_v1", "downloaded_at_utc": downloaded.isoformat().replace("+00:00", "Z")}

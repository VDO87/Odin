"""Canonical, immutable contract for locally imported historical candles."""

from __future__ import annotations

CANONICAL_CANDLE_SCHEMA_VERSION = "odin.candles.csv/v1"

CANONICAL_CANDLE_COLUMNS = (
    "symbol",
    "timeframe",
    "timestamp_utc",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source",
    "source_version",
    "schema_version",
    "provenance",
    "license",
    "hash",
)

SUPPORTED_TIMEFRAMES_SECONDS = {
    "M1": 60,
    "M5": 5 * 60,
    "M15": 15 * 60,
    "H1": 60 * 60,
}

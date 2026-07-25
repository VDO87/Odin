"""Fail-closed local Forex OHLCV CSV import with provenance."""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path

from odin.contracts.market_data import Candle

REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume", "spread")


def load_forex_history(
    path: str,
    *,
    symbol: str,
    timeframe: str,
    source: str,
) -> dict[str, object]:
    """Load local CSV only; invalid data returns a blocked report and no candles."""
    file_path = Path(path)
    if not file_path.is_file() or not symbol or not timeframe or not source:
        return _blocked("history_file_or_provenance_missing")
    try:
        with file_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = tuple(reader.fieldnames or ())
            missing = [column for column in REQUIRED_COLUMNS if column not in columns]
            if missing:
                return _blocked("history_schema_invalid", missing_columns=missing)
            candles = [_candle_from_row(row, symbol=symbol, timeframe=timeframe) for row in reader]
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return _blocked("history_parse_failed", detail=str(error))

    issue = _validate_candles(candles)
    if issue:
        return _blocked(issue)
    return {
        "status": "OK",
        "component": "forex_history",
        "mode": "READ_ONLY_HISTORY",
        "source": source,
        "source_path": str(file_path),
        "symbol": symbol,
        "timeframe": timeframe,
        "candles_count": len(candles),
        "first_timestamp": candles[0].timestamp,
        "last_timestamp": candles[-1].timestamp,
        "candles": [candle.to_dict() for candle in candles],
        "safe_to_use_for_decision": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def assess_history_quality(
    history: dict[str, object], *, now: datetime | None = None,
    max_age: timedelta = timedelta(days=2),
) -> dict[str, object]:
    """Assess freshness and expected candle gaps without enabling decisions."""
    if history.get("status") != "OK":
        return _quality_blocked("history_not_available")
    candles = history.get("candles", [])
    expected = _timeframe_duration(str(history.get("timeframe", "")))
    if not isinstance(candles, list) or expected is None:
        return _quality_blocked("history_quality_input_invalid")
    timestamps = [datetime.fromisoformat(str(c["timestamp"]).replace("Z", "+00:00"))
                  for c in candles if isinstance(c, dict)]
    if len(timestamps) != len(candles) or not timestamps:
        return _quality_blocked("history_quality_input_invalid")
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    age = reference - timestamps[-1]
    gaps = [{"after": left.isoformat(), "before": right.isoformat()}
            for left, right in zip(timestamps, timestamps[1:]) if right - left > expected]
    fresh = age <= max_age
    return {"status": "OK" if fresh and not gaps else "WARNING",
            "component": "forex_history_quality", "mode": "READ_ONLY_HISTORY",
            "last_timestamp": timestamps[-1].isoformat(), "age_seconds": int(age.total_seconds()),
            "max_age_seconds": int(max_age.total_seconds()), "fresh": fresh,
            "gaps_count": len(gaps), "gaps": gaps, "safe_to_use_for_decision": False,
            "execution_allowed": False, "safe_to_trade": False, "real_trading": False}


def _timeframe_duration(timeframe: str) -> timedelta | None:
    return {"M1": timedelta(minutes=1), "M5": timedelta(minutes=5),
            "M15": timedelta(minutes=15), "H1": timedelta(hours=1)}.get(timeframe)


def _quality_blocked(reason: str) -> dict[str, object]:
    return {"status": "BLOCKED", "component": "forex_history_quality", "reason": reason,
            "safe_to_use_for_decision": False, "execution_allowed": False,
            "safe_to_trade": False, "real_trading": False}


def _candle_from_row(row: dict[str, str], *, symbol: str, timeframe: str) -> Candle:
    return Candle(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=row["timestamp"].strip(),
        open=float(row["open"]), high=float(row["high"]), low=float(row["low"]),
        close=float(row["close"]), volume=int(row["volume"]), spread=float(row["spread"]),
    )


def _validate_candles(candles: list[Candle]) -> str | None:
    if not candles:
        return "history_empty"
    timestamps: list[datetime] = []
    for candle in candles:
        timestamp = datetime.fromisoformat(candle.timestamp.replace("Z", "+00:00"))
        timestamps.append(timestamp)
        if min(candle.open, candle.close) < candle.low or max(candle.open, candle.close) > candle.high:
            return "history_ohlc_invalid"
        if candle.volume < 0 or candle.spread < 0:
            return "history_volume_or_spread_invalid"
    if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
        return "history_timestamps_not_strictly_ascending"
    return None


def _blocked(reason: str, **extra: object) -> dict[str, object]:
    return {
        "status": "BLOCKED", "component": "forex_history", "mode": "READ_ONLY_HISTORY",
        "reason": reason, **extra, "candles": [], "safe_to_use_for_decision": False,
        "execution_allowed": False, "safe_to_trade": False, "real_trading": False,
    }

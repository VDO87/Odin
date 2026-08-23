"""Fail-closed UTC freshness assessment for broker market timestamps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import math


@dataclass(frozen=True)
class MarketTimeAssessment:
    status: str
    age_seconds: float
    tick_time_raw: float | None
    tick_time_utc: str | None
    now_raw: str
    now_utc: str
    reason_codes: tuple[str, ...]


def assess_market_timestamp(
    tick_time_raw: object,
    *,
    now_utc: datetime,
    stale_threshold_seconds: int = 60,
    allowed_future_clock_skew_seconds: int = 2,
) -> MarketTimeAssessment:
    """Compare an MT5 Unix timestamp with an aware UTC clock without offset guessing."""
    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise ValueError("now_utc_must_be_timezone_aware")
    current = now_utc.astimezone(UTC)
    current_iso = current.isoformat()
    try:
        raw = float(tick_time_raw)
        if not math.isfinite(raw):
            raise ValueError
        tick_utc = datetime.fromtimestamp(raw, UTC)
    except (OverflowError, OSError, TypeError, ValueError):
        return MarketTimeAssessment(
            status="BLOCKED",
            age_seconds=float("nan"),
            tick_time_raw=None,
            tick_time_utc=None,
            now_raw=now_utc.isoformat(),
            now_utc=current_iso,
            reason_codes=("market_timestamp_invalid",),
        )

    age = current.timestamp() - raw
    if age < -allowed_future_clock_skew_seconds:
        status = "BLOCKED"
        reasons = ("future_market_timestamp", "clock_skew_detected")
    elif age < 0:
        status = "FRESH"
        reasons = ("clock_skew_within_tolerance",)
    elif age <= stale_threshold_seconds:
        status = "FRESH"
        reasons = ()
    else:
        status = "STALE"
        reasons = ("stale_data", "stale_data_threshold_exceeded")
    return MarketTimeAssessment(
        status=status,
        age_seconds=age,
        tick_time_raw=raw,
        tick_time_utc=tick_utc.isoformat(),
        now_raw=now_utc.isoformat(),
        now_utc=current_iso,
        reason_codes=reasons,
    )

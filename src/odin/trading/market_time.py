"""Fail-closed UTC normalization and freshness for broker market timestamps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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
    broker_server_time: str | None
    normalized_event_time_utc: str | None
    normalization_method: str
    observed_server_offset_seconds: int | None
    expected_server_offset_seconds: int | None
    normalization_confidence: str
    source_profile: str | None


@dataclass(frozen=True)
class BrokerTimeProfile:
    profile_id: str
    broker: str
    server: str
    server_timezone: str
    standard_offset_seconds: int
    daylight_offset_seconds: int
    dst_rule: str


@dataclass(frozen=True)
class BrokerTimestampNormalization:
    status: str
    broker_timestamp_raw: float | None
    broker_server_time: str | None
    raw_datetime_as_utc: str | None
    normalized_event_time_utc: str | None
    normalized_epoch: float | None
    normalization_method: str
    observed_server_offset_seconds: int | None
    expected_server_offset_seconds: int | None
    normalization_confidence: str
    source_profile: str | None
    reason_codes: tuple[str, ...]


OANDA_TMS_CET_CEST = BrokerTimeProfile(
    profile_id="oanda_tms_mt5_cet_cest_v1",
    broker="OANDA TMS Brokers S.A.",
    server="OANDATMS-MT5",
    server_timezone="Europe/Warsaw (CET/CEST)",
    standard_offset_seconds=3600,
    daylight_offset_seconds=7200,
    dst_rule="EU_LAST_SUNDAY_MARCH_TO_LAST_SUNDAY_OCTOBER_01UTC",
)


def _last_sunday(year: int, month: int) -> datetime:
    if month == 12:
        first_next = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        first_next = datetime(year, month + 1, 1, tzinfo=UTC)
    last_day = first_next - timedelta(days=1)
    return last_day - timedelta(days=(last_day.weekday() + 1) % 7)


def _eu_server_offset_seconds(event_utc: datetime, profile: BrokerTimeProfile) -> int:
    current = event_utc.astimezone(UTC)
    dst_start = _last_sunday(current.year, 3).replace(hour=1)
    dst_end = _last_sunday(current.year, 10).replace(hour=1)
    if dst_start <= current < dst_end:
        return profile.daylight_offset_seconds
    return profile.standard_offset_seconds


def _profile_for(broker: str | None, server: str | None) -> BrokerTimeProfile | None:
    if broker == OANDA_TMS_CET_CEST.broker and server == OANDA_TMS_CET_CEST.server:
        return OANDA_TMS_CET_CEST
    return None


def normalize_broker_timestamp(
    broker_timestamp_raw: object,
    *,
    now_utc: datetime,
    broker: str | None = None,
    server: str | None = None,
    source_observed_offset_seconds: int | None = None,
    allowed_future_clock_skew_seconds: int = 2,
) -> BrokerTimestampNormalization:
    """Normalize a source timestamp only when an exact audited profile proves the offset."""
    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise ValueError("now_utc_must_be_timezone_aware")
    current = now_utc.astimezone(UTC)
    try:
        if not isinstance(broker_timestamp_raw, (str, int, float)):
            raise TypeError
        raw = float(broker_timestamp_raw)
        if not math.isfinite(raw):
            raise ValueError
        raw_as_utc = datetime.fromtimestamp(raw, UTC)
    except (OverflowError, OSError, TypeError, ValueError):
        return BrokerTimestampNormalization(
            status="BLOCKED",
            broker_timestamp_raw=None,
            broker_server_time=None,
            raw_datetime_as_utc=None,
            normalized_event_time_utc=None,
            normalized_epoch=None,
            normalization_method="NONE",
            observed_server_offset_seconds=None,
            expected_server_offset_seconds=None,
            normalization_confidence="NONE",
            source_profile=None,
            reason_codes=("market_timestamp_invalid",),
        )

    profile = _profile_for(broker, server)
    source_identity_supplied = broker is not None or server is not None
    if profile is None and not source_identity_supplied:
        return BrokerTimestampNormalization(
            status="ACCEPTED",
            broker_timestamp_raw=raw,
            broker_server_time=None,
            raw_datetime_as_utc=raw_as_utc.isoformat(),
            normalized_event_time_utc=raw_as_utc.isoformat(),
            normalized_epoch=raw,
            normalization_method="RAW_UTC_NO_TRANSFORMATION",
            observed_server_offset_seconds=0,
            expected_server_offset_seconds=0,
            normalization_confidence="HIGH",
            source_profile=None,
            reason_codes=(),
        )

    if profile is None:
        return BrokerTimestampNormalization(
            status="BLOCKED",
            broker_timestamp_raw=raw,
            broker_server_time=raw_as_utc.replace(tzinfo=None).isoformat(),
            raw_datetime_as_utc=raw_as_utc.isoformat(),
            normalized_event_time_utc=None,
            normalized_epoch=None,
            normalization_method="NONE",
            observed_server_offset_seconds=None,
            expected_server_offset_seconds=None,
            normalization_confidence="NONE",
            source_profile=None,
            reason_codes=("broker_time_profile_not_found",),
        )

    candidates: list[tuple[int, datetime]] = []
    for offset in (profile.standard_offset_seconds, profile.daylight_offset_seconds):
        candidate = datetime.fromtimestamp(raw - offset, UTC)
        if _eu_server_offset_seconds(candidate, profile) == offset:
            candidates.append((offset, candidate))
    broker_server_time = f"{raw_as_utc.replace(tzinfo=None).isoformat()}[{profile.server_timezone}]"
    if not candidates:
        return BrokerTimestampNormalization(
            status="BLOCKED",
            broker_timestamp_raw=raw,
            broker_server_time=broker_server_time,
            raw_datetime_as_utc=raw_as_utc.isoformat(),
            normalized_event_time_utc=None,
            normalized_epoch=None,
            normalization_method="SOURCE_PROFILE_REJECTED",
            observed_server_offset_seconds=source_observed_offset_seconds,
            expected_server_offset_seconds=None,
            normalization_confidence="NONE",
            source_profile=profile.profile_id,
            reason_codes=("unexpected_broker_time_offset",),
        )
    if source_observed_offset_seconds is not None:
        matching = [
            item for item in candidates if item[0] == source_observed_offset_seconds
        ]
        if len(matching) != 1:
            expected = candidates[0][0] if len(candidates) == 1 else None
            return BrokerTimestampNormalization(
                status="BLOCKED",
                broker_timestamp_raw=raw,
                broker_server_time=broker_server_time,
                raw_datetime_as_utc=raw_as_utc.isoformat(),
                normalized_event_time_utc=None,
                normalized_epoch=None,
                normalization_method="SOURCE_PROFILE_OFFSET_MISMATCH",
                observed_server_offset_seconds=source_observed_offset_seconds,
                expected_server_offset_seconds=expected,
                normalization_confidence="NONE",
                source_profile=profile.profile_id,
                reason_codes=("unexpected_broker_time_offset",),
            )
        candidates = matching
    if len(candidates) != 1:
        return BrokerTimestampNormalization(
            status="BLOCKED",
            broker_timestamp_raw=raw,
            broker_server_time=broker_server_time,
            raw_datetime_as_utc=raw_as_utc.isoformat(),
            normalized_event_time_utc=None,
            normalized_epoch=None,
            normalization_method="SOURCE_PROFILE_AMBIGUOUS",
            observed_server_offset_seconds=source_observed_offset_seconds,
            expected_server_offset_seconds=None,
            normalization_confidence="NONE",
            source_profile=profile.profile_id,
            reason_codes=("broker_time_dst_ambiguous",),
        )

    offset, normalized = candidates[0]
    if normalized.timestamp() > current.timestamp() + allowed_future_clock_skew_seconds:
        return BrokerTimestampNormalization(
            status="BLOCKED",
            broker_timestamp_raw=raw,
            broker_server_time=broker_server_time,
            raw_datetime_as_utc=raw_as_utc.isoformat(),
            normalized_event_time_utc=normalized.isoformat(),
            normalized_epoch=normalized.timestamp(),
            normalization_method="SOURCE_PROFILE_CET_CEST_EU_V1",
            observed_server_offset_seconds=offset,
            expected_server_offset_seconds=offset,
            normalization_confidence="HIGH",
            source_profile=profile.profile_id,
            reason_codes=("future_market_timestamp", "clock_skew_detected"),
        )
    return BrokerTimestampNormalization(
        status="NORMALIZED",
        broker_timestamp_raw=raw,
        broker_server_time=broker_server_time,
        raw_datetime_as_utc=raw_as_utc.isoformat(),
        normalized_event_time_utc=normalized.isoformat(),
        normalized_epoch=normalized.timestamp(),
        normalization_method="SOURCE_PROFILE_CET_CEST_EU_V1",
        observed_server_offset_seconds=offset,
        expected_server_offset_seconds=offset,
        normalization_confidence="HIGH",
        source_profile=profile.profile_id,
        reason_codes=(),
    )


def assess_market_timestamp(
    tick_time_raw: object,
    *,
    now_utc: datetime,
    stale_threshold_seconds: int = 60,
    allowed_future_clock_skew_seconds: int = 2,
    broker: str | None = None,
    server: str | None = None,
    source_observed_offset_seconds: int | None = None,
) -> MarketTimeAssessment:
    """Normalize an audited source timestamp, then assess freshness in UTC."""
    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise ValueError("now_utc_must_be_timezone_aware")
    current = now_utc.astimezone(UTC)
    current_iso = current.isoformat()
    normalization = normalize_broker_timestamp(
        tick_time_raw,
        now_utc=current,
        broker=broker,
        server=server,
        source_observed_offset_seconds=source_observed_offset_seconds,
        allowed_future_clock_skew_seconds=allowed_future_clock_skew_seconds,
    )
    if normalization.status == "BLOCKED" or normalization.normalized_epoch is None:
        return MarketTimeAssessment(
            status="BLOCKED",
            age_seconds=(
                current.timestamp() - normalization.broker_timestamp_raw
                if normalization.broker_timestamp_raw is not None
                else float("nan")
            ),
            tick_time_raw=normalization.broker_timestamp_raw,
            tick_time_utc=normalization.raw_datetime_as_utc,
            now_raw=now_utc.isoformat(),
            now_utc=current_iso,
            reason_codes=normalization.reason_codes,
            broker_server_time=normalization.broker_server_time,
            normalized_event_time_utc=normalization.normalized_event_time_utc,
            normalization_method=normalization.normalization_method,
            observed_server_offset_seconds=normalization.observed_server_offset_seconds,
            expected_server_offset_seconds=normalization.expected_server_offset_seconds,
            normalization_confidence=normalization.normalization_confidence,
            source_profile=normalization.source_profile,
        )

    age = current.timestamp() - normalization.normalized_epoch
    reasons: tuple[str, ...]
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
        tick_time_raw=normalization.broker_timestamp_raw,
        tick_time_utc=normalization.raw_datetime_as_utc,
        now_raw=now_utc.isoformat(),
        now_utc=current_iso,
        reason_codes=reasons,
        broker_server_time=normalization.broker_server_time,
        normalized_event_time_utc=normalization.normalized_event_time_utc,
        normalization_method=normalization.normalization_method,
        observed_server_offset_seconds=normalization.observed_server_offset_seconds,
        expected_server_offset_seconds=normalization.expected_server_offset_seconds,
        normalization_confidence=normalization.normalization_confidence,
        source_profile=normalization.source_profile,
    )

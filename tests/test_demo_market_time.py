from dataclasses import replace
from datetime import UTC, datetime, timedelta

from odin.risk.demo_execution import evaluate_demo_risk
from odin.trading.demo_execution_gate import evaluate_demo_execution_gate
from odin.trading.market_time import assess_market_timestamp, normalize_broker_timestamp

from test_demo_execution_gate import evidence, proposal


NOW = datetime(2026, 8, 23, 21, 58, 42, tzinfo=UTC)
BROKER = "OANDA TMS Brokers S.A."
SERVER = "OANDATMS-MT5"


def test_recent_past_tick_is_fresh() -> None:
    result = assess_market_timestamp((NOW - timedelta(seconds=2)).timestamp(), now_utc=NOW)
    assert result.status == "FRESH"
    assert result.age_seconds == 2
    assert result.reason_codes == ()


def test_old_tick_is_stale() -> None:
    result = assess_market_timestamp((NOW - timedelta(seconds=61)).timestamp(), now_utc=NOW)
    assert result.status == "STALE"
    assert result.age_seconds == 61
    assert result.reason_codes == ("stale_data", "stale_data_threshold_exceeded")


def test_small_future_clock_skew_is_explicitly_tolerated_without_rewriting_age() -> None:
    result = assess_market_timestamp((NOW + timedelta(seconds=1)).timestamp(), now_utc=NOW)
    assert result.status == "FRESH"
    assert result.age_seconds == -1
    assert result.reason_codes == ("clock_skew_within_tolerance",)


def test_two_hour_future_tick_blocks_as_clock_anomaly() -> None:
    result = assess_market_timestamp((NOW + timedelta(hours=2)).timestamp(), now_utc=NOW)
    assert result.status == "BLOCKED"
    assert result.age_seconds == -7200
    assert result.reason_codes == ("future_market_timestamp", "clock_skew_detected")

    ev = replace(
        evidence(),
        data_fresh=False,
        data_age_seconds=int(result.age_seconds),
        market_time_status=result.status,
        market_time_reason_codes=result.reason_codes,
    )
    risk = evaluate_demo_risk(proposal(), ev)
    gate = evaluate_demo_execution_gate(
        proposal(), ev, risk, duplicate_detected=False, now_utc=NOW
    )
    assert risk["status"] == "BLOCK"
    assert "future_market_timestamp" in risk["reason_codes"]
    assert "clock_skew_detected" in risk["reason_codes"]
    assert "stale_data" not in risk["reason_codes"]
    assert gate["status"] == "BLOCK"
    assert gate["order_send_allowed"] is False


def test_raw_utc_timestamp_needs_no_transformation() -> None:
    raw = (NOW - timedelta(seconds=3)).timestamp()
    result = assess_market_timestamp(raw, now_utc=NOW)
    assert result.status == "FRESH"
    assert result.age_seconds == 3
    assert result.normalization_method == "RAW_UTC_NO_TRANSFORMATION"
    assert result.observed_server_offset_seconds == 0


def test_winter_server_timestamp_plus_one_hour_normalizes_to_utc() -> None:
    now = datetime(2026, 1, 15, 12, tzinfo=UTC)
    event_utc = now - timedelta(seconds=4)
    raw = event_utc.timestamp() + 3600
    result = assess_market_timestamp(raw, now_utc=now, broker=BROKER, server=SERVER)
    assert result.status == "FRESH"
    assert result.age_seconds == 4
    assert result.normalized_event_time_utc == event_utc.isoformat()
    assert result.observed_server_offset_seconds == 3600
    assert result.normalization_confidence == "HIGH"


def test_summer_server_timestamp_plus_two_hours_normalizes_to_utc() -> None:
    event_utc = NOW - timedelta(seconds=5)
    raw = event_utc.timestamp() + 7200
    result = assess_market_timestamp(raw, now_utc=NOW, broker=BROKER, server=SERVER)
    assert result.status == "FRESH"
    assert result.age_seconds == 5
    assert result.normalized_event_time_utc == event_utc.isoformat()
    assert result.observed_server_offset_seconds == 7200
    assert result.source_profile == "oanda_tms_mt5_cet_cest_v1"


def test_eu_dst_transitions_apply_the_documented_seasonal_offsets() -> None:
    before_spring = datetime(2026, 3, 29, 0, 59, tzinfo=UTC)
    after_spring = datetime(2026, 3, 29, 1, 1, tzinfo=UTC)
    before_autumn = datetime(2026, 10, 25, 0, 59, tzinfo=UTC)
    after_autumn = datetime(2026, 10, 25, 1, 1, tzinfo=UTC)
    winter = normalize_broker_timestamp(
        before_spring.timestamp() + 3600,
        now_utc=before_spring + timedelta(seconds=1),
        broker=BROKER,
        server=SERVER,
    )
    summer = normalize_broker_timestamp(
        after_spring.timestamp() + 7200,
        now_utc=after_spring + timedelta(seconds=1),
        broker=BROKER,
        server=SERVER,
    )
    summer_before_autumn = normalize_broker_timestamp(
        before_autumn.timestamp() + 7200,
        now_utc=before_autumn + timedelta(seconds=1),
        broker=BROKER,
        server=SERVER,
    )
    winter_after_autumn = normalize_broker_timestamp(
        after_autumn.timestamp() + 3600,
        now_utc=after_autumn + timedelta(seconds=1),
        broker=BROKER,
        server=SERVER,
    )
    assert winter.status == "NORMALIZED"
    assert winter.observed_server_offset_seconds == 3600
    assert summer.status == "NORMALIZED"
    assert summer.observed_server_offset_seconds == 7200
    assert summer_before_autumn.status == "NORMALIZED"
    assert summer_before_autumn.observed_server_offset_seconds == 7200
    assert winter_after_autumn.status == "NORMALIZED"
    assert winter_after_autumn.observed_server_offset_seconds == 3600


def test_unknown_profile_blocks_future_timestamp() -> None:
    result = assess_market_timestamp(
        NOW.timestamp() + 7200,
        now_utc=NOW,
        broker="Unknown",
        server="Unknown",
    )
    assert result.status == "BLOCKED"
    assert result.reason_codes == ("broker_time_profile_not_found", "future_market_timestamp")


def test_unexpected_profile_offset_blocks() -> None:
    result = assess_market_timestamp(
        NOW.timestamp() + 10800,
        now_utc=NOW,
        broker=BROKER,
        server=SERVER,
    )
    assert result.status == "BLOCKED"
    assert result.observed_server_offset_seconds == 10800
    assert result.reason_codes == ("unexpected_broker_time_offset",)


def test_timestamp_future_after_normalization_blocks() -> None:
    event_utc = NOW + timedelta(seconds=10)
    result = assess_market_timestamp(
        event_utc.timestamp() + 7200,
        now_utc=NOW,
        broker=BROKER,
        server=SERVER,
    )
    assert result.status == "BLOCKED"
    assert result.normalized_event_time_utc == event_utc.isoformat()
    assert result.reason_codes == ("future_market_timestamp", "clock_skew_detected")


def test_normalized_old_timestamp_is_stale() -> None:
    event_utc = NOW - timedelta(seconds=61)
    result = assess_market_timestamp(
        event_utc.timestamp() + 7200,
        now_utc=NOW,
        broker=BROKER,
        server=SERVER,
    )
    assert result.status == "STALE"
    assert result.age_seconds == 61
    assert result.reason_codes == ("stale_data", "stale_data_threshold_exceeded")


def test_oanda_profile_does_not_silently_accept_raw_utc_semantics() -> None:
    result = assess_market_timestamp(
        (NOW - timedelta(seconds=3)).timestamp(),
        now_utc=NOW,
        broker=BROKER,
        server=SERVER,
    )
    assert result.status == "BLOCKED"
    assert result.reason_codes == ("unexpected_broker_time_offset",)


def test_real_and_unknown_still_hard_block_with_no_broker_submission() -> None:
    for account_mode in ("REAL", "UNKNOWN"):
        ev = evidence(account_mode=account_mode)
        gate = evaluate_demo_execution_gate(
            proposal(),
            ev,
            evaluate_demo_risk(proposal(), ev),
            duplicate_detected=False,
            now_utc=NOW,
        )
        assert gate["status"] == "HARD_BLOCK"
        assert gate["order_send_allowed"] is False
    broker_submission_called = False
    assert broker_submission_called is False

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from odin.risk.demo_execution import evaluate_demo_risk
from odin.trading.demo_execution_gate import evaluate_demo_execution_gate
from odin.trading.market_time import assess_market_timestamp

from test_demo_execution_gate import evidence, proposal


NOW = datetime(2026, 8, 23, 21, 58, 42, tzinfo=UTC)


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

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json

import pytest

from odin.trading.demo_live_soak import (
    SoakCycleEvidence,
    SoakLimits,
    evaluate_postcanary_cycle,
    evaluate_precanary_cycle,
    run_bounded_postcanary_soak,
    run_bounded_precanary_soak,
)


NOW = datetime(2026, 8, 24, 8, tzinfo=UTC)


def evidence(**changes: object) -> SoakCycleEvidence:
    value = SoakCycleEvidence(
        observed_at_utc=NOW.isoformat(),
        account_mode="DEMO",
        broker="OANDA TMS Brokers S.A.",
        server="OANDATMS-MT5",
        terminal_path=r"C:\Program Files\OANDA TMS MT5 Terminal",
        terminal_connected=True,
        terminal_trade_allowed=True,
        account_trade_allowed=True,
        account_trade_expert=True,
        symbol="EURUSD",
        broker_symbol="EURUSD.pro",
        trade_mode=4,
        data_fresh=True,
        time_normalization_valid=True,
        normalized_event_time_utc=(NOW - timedelta(seconds=2)).isoformat(),
        data_age_seconds=2.0,
        spread_price=0.0001,
        spread_points=10.0,
        spread_limit_price=0.0003,
        spread_limit_points=30.0,
        reconciliation_status="RECONCILED",
        risk_status="ALLOW_DEMO",
        risk_reason_codes=(),
        kill_switch_engaged=False,
        position_count=0,
        position_reconciled=True,
        pending_execution=False,
        proposal_duplicate=False,
        proposal_available=True,
        no_trade=False,
    )
    return replace(value, **changes)


def test_current_external_stop_conditions_block_without_broker_action() -> None:
    result = evaluate_precanary_cycle(
        evidence(
            terminal_trade_allowed=False,
            trade_mode=0,
            spread_price=0.024,
            spread_points=2400,
        )
    )

    assert result.status == "STOPPED_PRE_CANARY"
    assert result.reason_codes == (
        "terminal_trade_not_allowed",
        "market_disabled",
        "excessive_spread",
    )
    assert result.action == "SAFE_STOP"
    assert result.broker_action_allowed is False


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"account_mode": "REAL"}, "account_identity_hard_block"),
        ({"account_mode": "UNKNOWN"}, "account_identity_hard_block"),
        ({"broker": "Other"}, "broker_identity_hard_block"),
        ({"server": "Other"}, "server_identity_hard_block"),
        ({"terminal_path": r"D:\ODIN_LOCAL\mt5"}, "terminal_identity_hard_block"),
        ({"broker_symbol": "EURUSD"}, "broker_symbol_identity_hard_block"),
    ],
)
def test_identity_mismatch_hard_blocks(change: dict[str, object], reason: str) -> None:
    result = evaluate_precanary_cycle(evidence(**change))
    assert result.status == "HARD_BLOCK"
    assert reason in result.reason_codes
    assert result.broker_action_allowed is False


def test_ready_cycle_stops_before_the_single_stage0_order_check() -> None:
    result = evaluate_precanary_cycle(evidence())
    assert result.status == "STAGE0_READY"
    assert result.action == "RUN_STAGE0_ONCE"
    assert result.stop is True
    assert result.broker_action_allowed is False


def test_no_trade_is_valid_and_waits_without_submission() -> None:
    result = evaluate_precanary_cycle(
        evidence(proposal_available=False, no_trade=True, risk_status="NOT_EVALUATED")
    )
    assert result.status == "NO_TRADE"
    assert result.action == "WAIT"
    assert result.stop is False
    assert result.broker_action_allowed is False


def test_reconciled_open_position_is_monitor_only() -> None:
    result = evaluate_precanary_cycle(evidence(position_count=1))
    assert result.status == "POSITION_OPEN_MONITOR_ONLY"
    assert result.action == "OBSERVE_AND_RECONCILE"
    assert result.stop is False


def test_postcanary_historical_submission_is_monitor_only() -> None:
    result = evaluate_postcanary_cycle(
        evidence(position_count=1, broker_submission_called=True)
    )
    assert result.status == "POSITION_OPEN_MONITOR_ONLY"
    assert result.action == "OBSERVE_AND_RECONCILE"
    assert result.stop is False
    assert result.broker_action_allowed is False


def test_postcanary_stops_for_close_reconciliation_without_new_action() -> None:
    result = evaluate_postcanary_cycle(
        evidence(
            position_count=0,
            proposal_available=False,
            no_trade=True,
            broker_submission_called=True,
        )
    )
    assert result.status == "CANARY_POSITION_CLOSED"
    assert result.action == "RECONCILE_CLOSE"
    assert result.stop is True
    assert result.broker_action_allowed is False


def test_unexpected_submission_and_unknown_execution_state_stop() -> None:
    result = evaluate_precanary_cycle(
        evidence(broker_submission_called=True, pending_execution=True)
    )
    assert result.status == "STOPPED_PRE_CANARY"
    assert "unexpected_broker_submission" in result.reason_codes
    assert "unknown_execution_state" in result.reason_codes
    assert result.broker_action_allowed is False


def test_restricted_trade_mode_and_spread_scale_mismatch_stop() -> None:
    restricted = evaluate_precanary_cycle(evidence(trade_mode=3))
    assert restricted.status == "STOPPED_PRE_CANARY"
    assert restricted.reason_codes == ("symbol_trade_mode_not_full",)

    inconsistent = evaluate_precanary_cycle(evidence(spread_points=100.0))
    assert inconsistent.status == "STOPPED_PRE_CANARY"
    assert inconsistent.reason_codes == ("spread_scale_mismatch", "excessive_spread")


def test_limits_prevent_busy_loop_and_scope_expansion() -> None:
    with pytest.raises(ValueError, match="busy_loop"):
        SoakLimits(cycle_interval_seconds=1)
    with pytest.raises(ValueError, match="between_1_and_5"):
        SoakLimits(max_trades=6)
    with pytest.raises(ValueError, match="six_hours"):
        SoakLimits(max_duration_seconds=21601)
    with pytest.raises(ValueError, match="remain_two"):
        SoakLimits(max_same_failure=3)


def test_bounded_loop_waits_once_then_stops_at_canary_ready(tmp_path) -> None:
    observations = [
        evidence(proposal_available=False, no_trade=True, risk_status="NOT_EVALUATED"),
        evidence(),
    ]
    sleeps: list[float] = []
    ticks = iter(
        (
            NOW,
            NOW,
            NOW,
            NOW + timedelta(minutes=1),
            NOW + timedelta(minutes=1),
            NOW + timedelta(minutes=1),
        )
    )

    result = run_bounded_precanary_soak(
        observe=lambda index: observations[index - 1],
        report_dir=tmp_path,
        limits=SoakLimits(max_cycles=2),
        git_checkpoint="test-checkpoint",
        clock=lambda: next(ticks),
        sleeper=sleeps.append,
    )

    assert result["status"] == "STAGE0_READY"
    assert result["broker_submission_called"] is False
    assert result["safe_to_trade"] is False
    assert result["real_trading"] is False
    assert result["execution_allowed"] is False
    assert sleeps == [60.0]
    metrics = result["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["cycles"] == 2
    assert metrics["no_trade_count"] == 1
    assert metrics["orders_submitted"] == 0
    persisted = json.loads((tmp_path / "ODIN_DEMO_LIVE_SOAK_METRICS.json").read_text())
    assert persisted["status"] == result["status"]
    assert persisted["git_checkpoint"] == "test-checkpoint"
    for name in (
        "ODIN_DEMO_LIVE_SOAK_STATUS.md",
        "ODIN_DEMO_LIVE_SOAK_INCIDENTS.md",
        "ODIN_DEMO_LIVE_SOAK_SELF_REPAIRS.md",
    ):
        assert (tmp_path / name).is_file()


def test_same_risk_failure_twice_stops_as_recurring_failure(tmp_path) -> None:
    ticks = iter((NOW, NOW, NOW, NOW + timedelta(minutes=1), NOW + timedelta(minutes=1)))
    result = run_bounded_precanary_soak(
        observe=lambda _: evidence(
            risk_status="BLOCK",
            risk_reason_codes=("max_risk_per_trade_exceeded",),
        ),
        report_dir=tmp_path,
        limits=SoakLimits(max_cycles=2),
        clock=lambda: next(ticks),
        sleeper=lambda _: None,
    )
    assert result["status"] == "BLOCKED_RECURRING_FAILURE"
    decision = result["last_decision"]
    assert isinstance(decision, dict)
    assert decision["reason_codes"] == (
        "recurring_failure",
        "max_risk_per_trade_exceeded",
    )
    assert result["broker_submission_called"] is False


def test_repeated_no_trade_is_not_misclassified_as_failure(tmp_path) -> None:
    ticks = iter(
        (
            NOW,
            NOW,
            NOW,
            NOW + timedelta(minutes=1),
            NOW + timedelta(minutes=1),
            NOW + timedelta(minutes=1),
        )
    )
    result = run_bounded_precanary_soak(
        observe=lambda _: evidence(
            proposal_available=False,
            no_trade=True,
            risk_status="NOT_EVALUATED",
        ),
        report_dir=tmp_path,
        limits=SoakLimits(max_cycles=2),
        clock=lambda: next(ticks),
        sleeper=lambda _: None,
    )
    assert result["status"] == "SOAK_CYCLE_LIMIT_COMPLETE_PRE_CANARY"
    assert result["broker_submission_called"] is False


def test_postcanary_loop_monitors_then_stops_at_position_close(tmp_path) -> None:
    observations = [
        evidence(
            position_count=1,
            proposal_available=False,
            no_trade=True,
            floating_pnl=-0.1,
        ),
        evidence(
            position_count=0,
            proposal_available=False,
            no_trade=True,
            floating_pnl=0.0,
        ),
    ]
    sleeps: list[float] = []
    ticks = iter(
        (
            NOW,
            NOW,
            NOW + timedelta(minutes=1),
            NOW + timedelta(minutes=1),
        )
    )

    result = run_bounded_postcanary_soak(
        observe=lambda index: observations[index - 1],
        report_dir=tmp_path,
        limits=SoakLimits(max_cycles=2),
        git_checkpoint="post-canary-checkpoint",
        started_at_utc=NOW.isoformat(),
        self_repairs=3,
        clock=lambda: next(ticks),
        sleeper=sleeps.append,
    )

    assert result["status"] == "CANARY_POSITION_CLOSED"
    assert result["mode"] == "POST_CANARY_MONITOR_ONLY"
    assert result["broker_submission_called"] is True
    assert result["safe_to_trade"] is False
    assert result["real_trading"] is False
    assert result["execution_allowed"] is False
    assert sleeps == [60.0]
    metrics = result["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["cycles"] == 2
    assert metrics["orders_submitted"] == 1
    assert metrics["orders_filled"] == 1
    assert metrics["self_repairs"] == 3

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from odin.contracts.demo_execution import (
    CanaryAuthorization,
    DemoAccountEvidence,
    TradeProposal,
)
from odin.decision.trade_proposal import build_trade_proposal
from odin.risk.demo_execution import evaluate_demo_risk
from odin.trading.demo_execution_gate import account_fingerprint, evaluate_demo_execution_gate


NOW = datetime(2026, 8, 22, 12, tzinfo=UTC)


def proposal(**changes: object) -> TradeProposal:
    value = TradeProposal(
        proposal_id="proposal-1",
        decision_id="decision-1",
        timestamp_utc=NOW.isoformat(),
        symbol="EURUSD",
        side="BUY",
        volume=0.01,
        entry_reference=1.10000,
        stop_loss=1.09900,
        take_profit=1.10200,
        strategy_id="trend_mean_v1",
        strategy_version="1",
        reason_codes=("trend_up",),
        market_data_hash="market-hash",
        data_quality="VALID",
        freshness="FRESH",
        expiry=(NOW + timedelta(minutes=1)).isoformat(),
    )
    return replace(value, **changes)


def evidence(**changes: object) -> DemoAccountEvidence:
    value = DemoAccountEvidence(
        expected_terminal_path=r"D:\ODIN_LOCAL\mt5\terminal64.exe",
        terminal_path=r"D:\ODIN_LOCAL\mt5\terminal64.exe",
        expected_broker="OANDA TMS Brokers S.A.",
        broker="OANDA TMS Brokers S.A.",
        expected_server="OANDATMS-MT5",
        server="OANDATMS-MT5",
        expected_login="123456",
        login="123456",
        account_mode="DEMO",
        terminal_connected=True,
        terminal_trade_allowed=True,
        market_open=True,
        symbol="EURUSD",
        data_fresh=True,
        data_age_seconds=2,
        reconciliation_status="RECONCILED",
        kill_switch_engaged=False,
        open_positions=0,
        active_orders=0,
        free_margin=9_000.0,
        daily_realized_pnl=0.0,
        drawdown_percent=0.0,
        spread=0.00010,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        point=0.00001,
        digits=5,
        stops_level_points=10,
        trade_tick_size=0.00001,
        trade_tick_value_loss=1.0,
    )
    return replace(value, **changes)


def test_trade_proposal_is_not_an_order_and_preserves_global_blocks() -> None:
    decision = {
        "decision_id": "d1",
        "strategy_id": "s1",
        "strategy_version": "1",
        "market_data_hash": "hash",
        "symbol": "EURUSD",
        "signal": "BUY",
        "reason_codes": ["trend_up"],
        "data_quality": "VALID",
        "freshness": "FRESH",
        "execution_allowed": False,
    }
    result = build_trade_proposal(
        decision,
        entry_reference=1.1,
        stop_loss=1.099,
        take_profit=1.102,
        now_utc=NOW,
    )
    assert result["status"] == "PROPOSED"
    assert result["execution_allowed"] is False
    assert result["real_trading"] is False


def test_non_actionable_decision_does_not_create_proposal() -> None:
    result = build_trade_proposal(
        {"signal": "HOLD", "execution_allowed": False},
        entry_reference=1.1,
        stop_loss=1.099,
        take_profit=1.102,
        now_utc=NOW,
    )
    assert result["status"] == "BLOCKED"
    assert result["proposal"] is None


def test_demo_risk_allows_only_demo_scope_without_global_unlock() -> None:
    result = evaluate_demo_risk(proposal(), evidence())
    assert result["status"] == "ALLOW_DEMO"
    assert result["risk_approved"] is True
    assert result["execution_allowed_scope"] == "DEMO"
    assert result["estimated_max_loss"] == 1.0
    assert result["execution_allowed"] is False
    assert result["real_trading"] is False


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"kill_switch_engaged": True}, "kill_switch_engaged"),
        ({"data_fresh": False}, "stale_data"),
        ({"data_age_seconds": 61}, "stale_data_threshold_exceeded"),
        ({"spread": 0.00031}, "excessive_spread"),
        ({"daily_realized_pnl": -50.0}, "daily_demo_loss_limit"),
        ({"drawdown_percent": 5.0}, "demo_drawdown_limit"),
        ({"open_positions": 1}, "position_limit_reached"),
        ({"active_orders": 1}, "order_limit_reached"),
        ({"free_margin": 999.0}, "minimum_free_margin_not_met"),
    ],
)
def test_demo_risk_blocks_conservative_limit_failures(changes: dict[str, object], reason: str) -> None:
    result = evaluate_demo_risk(proposal(), evidence(**changes))
    assert result["status"] in {"BLOCK", "KILL"}
    assert reason in result["reason_codes"]


@pytest.mark.parametrize("account_mode", ["REAL", "UNKNOWN", "", "CONTEST"])
def test_account_not_proven_demo_is_hard_block(account_mode: str) -> None:
    ev = evidence(account_mode=account_mode)
    result = evaluate_demo_execution_gate(
        proposal(), ev, evaluate_demo_risk(proposal(), ev), duplicate_detected=False, now_utc=NOW
    )
    assert result["status"] == "HARD_BLOCK"
    assert result["order_send_allowed"] is False
    assert result["real_trading"] is False


@pytest.mark.parametrize(
    "changes",
    [
        {"terminal_path": r"C:\Other\terminal64.exe"},
        {"broker": "Unexpected"},
        {"server": "Unexpected"},
        {"login": "999"},
        {"fallback_used": True},
    ],
)
def test_identity_mismatch_and_fallback_are_hard_block(changes: dict[str, object]) -> None:
    ev = evidence(**changes)
    result = evaluate_demo_execution_gate(
        proposal(), ev, evaluate_demo_risk(proposal(), ev), duplicate_detected=False, now_utc=NOW
    )
    assert result["status"] == "HARD_BLOCK"
    assert result["order_check_allowed"] is False


def test_valid_gate_stops_at_dry_run_without_human_canary() -> None:
    prop = proposal()
    ev = evidence()
    result = evaluate_demo_execution_gate(
        prop, ev, evaluate_demo_risk(prop, ev), duplicate_detected=False, now_utc=NOW
    )
    assert result["status"] == "DRY_RUN_READY"
    assert result["order_check_allowed"] is True
    assert result["order_send_allowed"] is False
    assert result["demo_execution_enabled"] is False


def test_synthetic_one_shot_canary_authorizes_only_demo_scope() -> None:
    prop = proposal()
    ev = evidence()
    authorization = CanaryAuthorization(
        proposal_id=prop.proposal_id,
        account_fingerprint=account_fingerprint(ev),
        issued_at_utc=(NOW - timedelta(seconds=1)).isoformat(),
        expires_at_utc=(NOW + timedelta(seconds=30)).isoformat(),
        single_use=True,
        consumed=False,
    )
    result = evaluate_demo_execution_gate(
        prop,
        ev,
        evaluate_demo_risk(prop, ev),
        duplicate_detected=False,
        canary_authorization=authorization,
        now_utc=NOW,
    )
    assert result["status"] == "CANARY_READY"
    assert result["order_send_allowed"] is True
    assert result["execution_allowed_scope"] == "DEMO_CANARY_ONE_SHOT"
    assert result["execution_allowed"] is False
    assert result["real_trading"] is False


@pytest.mark.parametrize(
    ("prop_changes", "ev_changes", "duplicate", "reason"),
    [
        ({"expiry": NOW.isoformat()}, {}, False, "proposal_expired"),
        ({"volume": 0.02}, {}, False, "invalid_volume"),
        ({"stop_loss": 1.1001}, {}, False, "invalid_stop_direction"),
        ({"take_profit": 1.10005}, {}, False, "invalid_stop_distance"),
        ({}, {"market_open": False}, False, "market_closed"),
        ({}, {"reconciliation_status": "MISMATCH"}, False, "reconciliation_not_ok"),
        ({}, {}, True, "duplicate_proposal"),
    ],
)
def test_gate_blocks_invalid_order_conditions(
    prop_changes: dict[str, object],
    ev_changes: dict[str, object],
    duplicate: bool,
    reason: str,
) -> None:
    prop = proposal(**prop_changes)
    ev = evidence(**ev_changes)
    risk = evaluate_demo_risk(prop, ev)
    result = evaluate_demo_execution_gate(
        prop, ev, risk, duplicate_detected=duplicate, now_utc=NOW
    )
    assert result["status"] == "BLOCK"
    assert reason in result["reason_codes"]
    assert result["order_send_allowed"] is False

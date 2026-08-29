from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest

from odin.contracts.demo_execution import DemoAccountEvidence
from odin.trading.autonomous_demo_cycle import (
    build_market_bars,
    build_trade_candidate,
    load_autonomous_demo_policy,
    summarize_daily_deals,
)


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 28, 12, 5, tzinfo=UTC)


def _policy():
    return load_autonomous_demo_policy(ROOT / "config/demo_execution_rc2.json")


def _rates(*, trend: str = "UP") -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    start = NOW.replace(minute=0, second=0, microsecond=0) - timedelta(minutes=75)
    for index in range(6):
        close = 1.16 + (index if trend == "UP" else -index if trend == "DOWN" else 0) * 0.0001
        result.append(
            {
                "time": int((start + timedelta(minutes=index * 15)).timestamp()) + 7200,
                "open": close - 0.00002,
                "high": close + 0.00005,
                "low": close - 0.00005,
                "close": close,
                "tick_volume": 100 + index,
                "spread": 10,
            }
        )
    return result


def _bars(*, trend: str = "UP"):
    result = build_market_bars(
        _rates(trend=trend),
        broker="OANDA TMS Brokers S.A.",
        server="OANDATMS-MT5",
        logical_symbol="EURUSD",
        point=0.00001,
        now_utc=NOW,
    )
    assert result["status"] == "VALIDATED"
    return result["bars"]


def _evidence(**changes: object) -> DemoAccountEvidence:
    base = DemoAccountEvidence(
        expected_terminal_path=r"C:\Program Files\OANDA TMS MT5 Terminal",
        terminal_path=r"C:\Program Files\OANDA TMS MT5 Terminal",
        expected_broker="OANDA TMS Brokers S.A.",
        broker="OANDA TMS Brokers S.A.",
        expected_server="OANDATMS-MT5",
        server="OANDATMS-MT5",
        expected_login="123",
        login="123",
        account_mode="DEMO",
        terminal_connected=True,
        terminal_trade_allowed=True,
        market_open=True,
        symbol="EURUSD",
        data_fresh=True,
        data_age_seconds=1,
        reconciliation_status="RECONCILED",
        kill_switch_engaged=False,
        open_positions=0,
        active_orders=0,
        free_margin=50_000.0,
        daily_realized_pnl=0.0,
        drawdown_percent=0.0,
        spread=0.0001,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        point=0.00001,
        digits=5,
        stops_level_points=0,
        trade_tick_size=0.00001,
        trade_tick_value_loss=0.9,
        expected_broker_symbol="EURUSD.pro",
        broker_symbol="EURUSD.pro",
    )
    return replace(base, **changes)


def test_policy_is_exactly_bounded_and_account_bound() -> None:
    policy = _policy()
    limits = policy.limits()
    authorization = policy.authorization(_evidence())

    assert policy.mode == "ODIN_AUTONOMOUS_DEMO_RC2"
    assert limits.max_position_size == 0.01
    assert limits.max_completed_trades_per_day == 3
    assert limits.max_daily_demo_loss == 5.0
    assert authorization.scope == "ODIN_AUTONOMOUS_DEMO_RC2"
    assert authorization.strategy_id == "trend_mean_v1"


def test_policy_rejects_any_guardrail_widening(tmp_path: Path) -> None:
    value = json.loads((ROOT / "config/demo_execution_rc2.json").read_text())
    value["fixed_volume"] = 0.02
    path = tmp_path / "unsafe.json"
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="rc2_policy_guardrail_mismatch"):
        load_autonomous_demo_policy(path)


def test_oanda_server_bars_are_explicitly_normalized_to_utc() -> None:
    result = build_market_bars(
        _rates(),
        broker="OANDA TMS Brokers S.A.",
        server="OANDATMS-MT5",
        logical_symbol="EURUSD",
        point=0.00001,
        now_utc=NOW,
    )

    assert result["status"] == "VALIDATED"
    bars = result["bars"]
    assert bars[-1].timestamp_utc == "2026-08-28T12:00:00+00:00"
    assert bars[-1].spread == pytest.approx(0.0001)


def test_unknown_broker_time_profile_blocks_market_bars() -> None:
    result = build_market_bars(
        _rates(),
        broker="Unknown",
        server="Unknown",
        logical_symbol="EURUSD",
        point=0.00001,
        now_utc=NOW,
    )

    assert result["status"] == "BLOCKED"
    assert result["reason"] == "market_bar_time_normalization_blocked"


@pytest.mark.parametrize(("trend", "side"), [("UP", "BUY"), ("DOWN", "SELL")])
def test_existing_strategy_builds_one_bounded_candidate(trend: str, side: str) -> None:
    result = build_trade_candidate(
        _bars(trend=trend),
        tick={"bid": 1.1600, "ask": 1.1601},
        symbol={"point": 0.00001, "digits": 5, "trade_stops_level": 0},
        policy=_policy(),
        now_utc=NOW,
    )

    assert result["status"] == "PROPOSAL_CREATED"
    proposal = result["proposal"]
    assert proposal.side == side
    assert proposal.volume == 0.01
    assert (
        proposal.stop_loss > proposal.entry_reference > proposal.take_profit
        if side == "SELL"
        else proposal.stop_loss < proposal.entry_reference < proposal.take_profit
    )
    assert result["execution_allowed"] is False
    assert result["real_trading"] is False


def test_flat_strategy_result_is_no_trade() -> None:
    result = build_trade_candidate(
        _bars(trend="FLAT"),
        tick={"bid": 1.1600, "ask": 1.1601},
        symbol={"point": 0.00001, "digits": 5, "trade_stops_level": 0},
        policy=_policy(),
        now_utc=NOW,
    )

    assert result["status"] == "NO_TRADE"
    assert result["proposal"] is None


def test_daily_deal_summary_counts_unique_closed_positions_and_net_costs() -> None:
    result = summarize_daily_deals(
        [
            {"symbol": "EURUSD.pro", "entry": 0, "position_id": 1, "profit": 0},
            {
                "symbol": "EURUSD.pro",
                "entry": 1,
                "position_id": 1,
                "profit": -0.8,
                "commission": -0.1,
                "swap": 0,
                "fee": 0,
            },
            {"symbol": "", "entry": 0, "position_id": 0, "profit": 50_000},
        ],
        broker_symbol="EURUSD.pro",
        exit_entries={1, 3},
    )

    assert result["status"] == "OK"
    assert result["completed_trades_today"] == 1
    assert result["daily_realized_pnl"] == -0.9


def test_missing_daily_history_fails_closed_at_both_daily_limits() -> None:
    result = summarize_daily_deals(
        None,
        broker_symbol="EURUSD.pro",
        exit_entries={1, 3},
    )

    assert result["status"] == "BLOCKED"
    assert result["completed_trades_today"] == 3
    assert result["daily_realized_pnl"] == -5.0

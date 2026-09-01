from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
from pathlib import Path

from odin.contracts.demo_execution import DemoAccountEvidence, TradeProposal
from odin.trading.demo_position_lifecycle import reconcile_latest_broker_close
from odin.trading.execution_ledger import (
    append_execution_event,
    confirm_execution_reconciliation,
    read_execution_ledger,
)


NOW = datetime(2026, 8, 28, 15, tzinfo=UTC)


class FakeMT5:
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1
    DEAL_ENTRY_OUT_BY = 3
    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1
    DEAL_REASON_SL = 4
    DEAL_REASON_TP = 5
    DEAL_REASON_CLIENT = 0
    DEAL_REASON_EXPERT = 3
    DEAL_REASON_SO = 6
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_STATE_FILLED = 4

    def __init__(self) -> None:
        proposal_id = "rc2-proposal"
        magic = int(hashlib.sha256(proposal_id.encode()).hexdigest()[:8], 16)
        comment = f"ODIN_RC2_{proposal_id[:12]}"
        entry_time = int((NOW - timedelta(hours=2)).timestamp()) + 7200
        close_time = int((NOW - timedelta(minutes=30)).timestamp()) + 7200
        self.deals: list[dict[str, object]] | None = [
            {
                "ticket": 1001,
                "order": 2001,
                "position_id": 77,
                "entry": self.DEAL_ENTRY_IN,
                "symbol": "EURUSD.pro",
                "type": self.DEAL_TYPE_BUY,
                "magic": magic,
                "comment": comment,
                "time": entry_time,
                "time_msc": entry_time * 1000,
                "price": 1.16,
                "volume": 0.01,
                "profit": 0.0,
                "commission": 0.0,
                "swap": 0.0,
                "fee": 0.0,
            },
            {
                "ticket": 1002,
                "order": 2002,
                "position_id": 77,
                "entry": self.DEAL_ENTRY_OUT,
                "symbol": "EURUSD.pro",
                "type": self.DEAL_TYPE_SELL,
                "time": close_time,
                "time_msc": close_time * 1000,
                "price": 1.159,
                "volume": 0.01,
                "profit": -0.88,
                "commission": 0.0,
                "swap": 0.0,
                "fee": 0.0,
                "reason": self.DEAL_REASON_SL,
            },
        ]
        self.orders: list[dict[str, object]] | None = [
            {
                "ticket": 2001,
                "position_id": 77,
                "symbol": "EURUSD.pro",
                "type": self.ORDER_TYPE_BUY,
                "state": self.ORDER_STATE_FILLED,
                "volume_initial": 0.01,
                "magic": magic,
                "comment": comment,
            },
            {"ticket": 2002},
        ]
        self.history_calls = 0

    def history_deals_get(
        self, *, position: int | None = None, ticket: int | None = None
    ) -> object:
        self.history_calls += 1
        if self.deals is None:
            return None
        if ticket is not None:
            return [item for item in self.deals if item.get("ticket") == ticket]
        assert position == 77
        return [item for item in self.deals if item.get("position_id") == position]

    def history_orders_get(
        self, *, position: int | None = None, ticket: int | None = None
    ) -> object:
        self.history_calls += 1
        if self.orders is None:
            return None
        if ticket is not None:
            return [item for item in self.orders if item.get("ticket") == ticket]
        assert position == 77
        return [item for item in self.orders if item.get("position_id") == position or item.get("ticket") == 2002]


def _proposal() -> TradeProposal:
    return TradeProposal(
        proposal_id="rc2-proposal",
        decision_id="rc2-decision",
        timestamp_utc=(NOW - timedelta(hours=2)).isoformat(),
        symbol="EURUSD",
        side="BUY",
        volume=0.01,
        entry_reference=1.16,
        stop_loss=1.159,
        take_profit=1.162,
        strategy_id="trend_mean_v1",
        strategy_version="1",
        reason_codes=("trend_up",),
        market_data_hash="abc",
        data_quality="VALID",
        freshness="FRESH",
        expiry=(NOW - timedelta(hours=1)).isoformat(),
    )


def _evidence() -> DemoAccountEvidence:
    return DemoAccountEvidence(
        expected_terminal_path="expected",
        terminal_path="expected",
        expected_broker="OANDA TMS Brokers S.A.",
        broker="OANDA TMS Brokers S.A.",
        expected_server="OANDATMS-MT5",
        server="OANDATMS-MT5",
        expected_login="1",
        login="1",
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
        free_margin=50_000,
        daily_realized_pnl=0,
        drawdown_percent=0,
        spread=0.0001,
        volume_min=0.01,
        volume_max=100,
        volume_step=0.01,
        point=0.00001,
        digits=5,
        stops_level_points=0,
        trade_tick_size=0.00001,
        trade_tick_value_loss=0.9,
        expected_broker_symbol="EURUSD.pro",
        broker_symbol="EURUSD.pro",
    )


def _open_reconciled_ledger(path: Path) -> None:
    append_execution_event(
        path=path,
        proposal=_proposal(),
        evidence=_evidence(),
        risk_result={"status": "ALLOW_DEMO", "risk_approved": True},
        execution_status="FILLED",
        reconciliation_status="PENDING",
        executed_volume=0.01,
        executed_price=1.16,
        ticket=2001,
    )
    result = confirm_execution_reconciliation(
        path=path,
        proposal_id="rc2-proposal",
        reconciliation_result={
            "status": "RECONCILED",
            "broker_is_source_of_truth": True,
        },
        position_id=77,
    )
    assert result["status"] == "RECONCILED"


def _filled_pending_ledger(path: Path) -> None:
    append_execution_event(
        path=path,
        proposal=_proposal(),
        evidence=_evidence(),
        risk_result={"status": "ALLOW_DEMO", "risk_approved": True},
        execution_status="FILLED",
        reconciliation_status="PENDING",
        order_send_result={
            "retcode": 10009,
            "deal": 1001,
            "order": 2001,
            "volume": 0.01,
            "price": 1.16,
        },
        executed_volume=0.01,
        executed_price=1.16,
        ticket=2001,
    )


def test_open_position_is_observed_without_history_or_mutation(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    _open_reconciled_ledger(path)
    mt5 = FakeMT5()

    result = reconcile_latest_broker_close(
        mt5,
        ledger_path=path,
        broker_positions=[{"ticket": 77}],
        broker_orders=[],
        broker="OANDA TMS Brokers S.A.",
        server="OANDATMS-MT5",
        point=0.00001,
        now_utc=NOW,
    )

    assert result["status"] == "POSITION_OPEN"
    assert mt5.history_calls == 0
    assert read_execution_ledger(path)["latest"]["execution_status"] == "RECONCILED"


def test_closed_position_is_proven_from_broker_history_and_reconciled(
    tmp_path: Path,
) -> None:
    path = tmp_path / "execution.jsonl"
    _open_reconciled_ledger(path)
    mt5 = FakeMT5()

    result = reconcile_latest_broker_close(
        mt5,
        ledger_path=path,
        broker_positions=[],
        broker_orders=[],
        broker="OANDA TMS Brokers S.A.",
        server="OANDATMS-MT5",
        point=0.00001,
        now_utc=NOW,
    )

    assert result["status"] == "CLOSED_AND_RECONCILED"
    assert result["realized_pnl"] == -0.88
    assert result["close_reason"] == "SL"
    latest = read_execution_ledger(path)["latest"]
    assert latest["execution_status"] == "CLOSED"
    assert latest["reconciliation_status"] == "RECONCILED"


def test_missing_exit_history_blocks_without_fabricating_close(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    _open_reconciled_ledger(path)
    mt5 = FakeMT5()
    mt5.deals = mt5.deals[:1] if mt5.deals is not None else []

    result = reconcile_latest_broker_close(
        mt5,
        ledger_path=path,
        broker_positions=[],
        broker_orders=[],
        broker="OANDA TMS Brokers S.A.",
        server="OANDATMS-MT5",
        point=0.00001,
        now_utc=NOW,
    )

    assert result["status"] == "RECONCILIATION_BLOCK"
    assert result["reason"] == "broker_close_history_incomplete"
    assert read_execution_ledger(path)["latest"]["execution_status"] == "RECONCILED"


def test_missing_position_id_is_recovered_from_exact_broker_history(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    _filled_pending_ledger(path)
    mt5 = FakeMT5()

    result = reconcile_latest_broker_close(
        mt5,
        ledger_path=path,
        broker_positions=[],
        broker_orders=[],
        broker="OANDA TMS Brokers S.A.",
        server="OANDATMS-MT5",
        point=0.00001,
        now_utc=NOW,
    )

    assert result["status"] == "CLOSED_AND_RECONCILED"
    assert result["position_id_recovered"] is True
    assert result["broker_submission_called"] is False
    ledger = read_execution_ledger(path)
    assert ledger["status"] == "OK"
    assert ledger["records_count"] == 3
    assert ledger["latest"]["execution_status"] == "CLOSED"
    assert ledger["latest"]["reconciliation_status"] == "RECONCILED"


def test_missing_position_id_blocks_mismatched_submission_history(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    _filled_pending_ledger(path)
    mt5 = FakeMT5()
    assert mt5.deals is not None
    mt5.deals[0]["comment"] = "not-odin"

    result = reconcile_latest_broker_close(
        mt5,
        ledger_path=path,
        broker_positions=[],
        broker_orders=[],
        broker="OANDA TMS Brokers S.A.",
        server="OANDATMS-MT5",
        point=0.00001,
        now_utc=NOW,
    )

    assert result["status"] == "RECONCILIATION_BLOCK"
    assert result["reason"] == "broker_submission_history_mismatch"
    assert result["broker_submission_called"] is False
    assert read_execution_ledger(path)["records_count"] == 1


def test_missing_position_id_blocks_non_unique_submission_history(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    _filled_pending_ledger(path)
    mt5 = FakeMT5()
    assert mt5.deals is not None
    mt5.deals.append(dict(mt5.deals[0]))

    result = reconcile_latest_broker_close(
        mt5,
        ledger_path=path,
        broker_positions=[],
        broker_orders=[],
        broker="OANDA TMS Brokers S.A.",
        server="OANDATMS-MT5",
        point=0.00001,
        now_utc=NOW,
    )

    assert result["status"] == "RECONCILIATION_BLOCK"
    assert result["reason"] == "broker_submission_history_not_unique"
    assert result["broker_submission_called"] is False
    assert read_execution_ledger(path)["records_count"] == 1

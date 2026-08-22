from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path

from odin.adapters.mt5.demo_execution_adapter import (
    perform_order_check,
    read_broker_execution_state,
    submit_demo_canary,
)
from odin.contracts.demo_execution import CanaryAuthorization, DemoAccountEvidence, TradeProposal
from odin.trading.demo_execution_gate import account_fingerprint
from odin.trading.demo_execution_service import run_demo_canary, run_demo_dry_run
from odin.trading.demo_reconciliation import reconcile_broker_truth, recovery_gate
from odin.trading.execution_ledger import (
    append_execution_event,
    read_execution_ledger,
    reserve_submission,
    submission_already_attempted,
)


NOW = datetime(2026, 8, 22, 12, tzinfo=UTC)


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    TRADE_ACTION_DEAL = 1
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_REJECT = 10006
    TRADE_RETCODE_INVALID_VOLUME = 10014
    TRADE_RETCODE_INVALID_STOPS = 10016
    TRADE_RETCODE_NO_MONEY = 10019
    TRADE_RETCODE_MARKET_CLOSED = 10018
    TRADE_RETCODE_REQUOTE = 10004
    TRADE_RETCODE_PRICE_CHANGED = 10020
    TRADE_RETCODE_TIMEOUT = 10012
    TRADE_RETCODE_INVALID_FILL = 10030

    def __init__(self) -> None:
        self.account = {
            "trade_mode": 0,
            "company": "OANDA TMS Brokers S.A.",
            "server": "OANDATMS-MT5",
            "login": 123456,
        }
        self.terminal = {
            "path": r"D:\ODIN_LOCAL\mt5\terminal64.exe",
            "connected": True,
            "trade_allowed": True,
            "tradeapi_disabled": False,
        }
        self.symbol = {"point": 0.00001, "filling_mode": 1}
        self.tick = {"ask": 1.10000, "bid": 1.09998}
        self.check_result: object = {"retcode": 0, "comment": "Done", "margin": 1.0}
        self.send_result: object = {
            "retcode": self.TRADE_RETCODE_DONE,
            "deal": 10,
            "order": 20,
            "volume": 0.01,
            "price": 1.10000,
            "comment": "Done",
        }
        self.check_calls = 0
        self.send_calls = 0
        self.positions: list[dict[str, object]] = []
        self.orders: list[dict[str, object]] = []
        self.materialize_fill = False

    def account_info(self) -> object:
        return self.account

    def terminal_info(self) -> object:
        return self.terminal

    def symbol_info(self, symbol: str) -> object:
        return self.symbol if symbol == "EURUSD" else None

    def symbol_info_tick(self, symbol: str) -> object:
        return self.tick if symbol == "EURUSD" else None

    def order_check(self, request: dict[str, object]) -> object:
        self.check_calls += 1
        return self.check_result

    def order_send(self, request: dict[str, object]) -> object:
        self.send_calls += 1
        if self.materialize_fill:
            self.positions = [
                {
                    "ticket": 30,
                    "symbol": request["symbol"],
                    "volume": request["volume"],
                    "price_open": request["price"],
                    "sl": request["sl"],
                    "tp": request["tp"],
                }
            ]
        return self.send_result

    def last_error(self) -> tuple[int, str]:
        return (-1, "fixture error")

    def positions_get(self) -> object:
        return self.positions

    def orders_get(self) -> object:
        return self.orders


def proposal(**changes: object) -> TradeProposal:
    value = TradeProposal(
        "proposal-1",
        "decision-1",
        NOW.isoformat(),
        "EURUSD",
        "BUY",
        0.01,
        1.10000,
        1.09900,
        1.10200,
        "trend_mean_v1",
        "1",
        ("trend_up",),
        "market-hash",
        "VALID",
        "FRESH",
        (NOW + timedelta(minutes=1)).isoformat(),
    )
    return replace(value, **changes)


def evidence(**changes: object) -> DemoAccountEvidence:
    value = DemoAccountEvidence(
        r"D:\ODIN_LOCAL\mt5\terminal64.exe",
        r"D:\ODIN_LOCAL\mt5\terminal64.exe",
        "OANDA TMS Brokers S.A.",
        "OANDA TMS Brokers S.A.",
        "OANDATMS-MT5",
        "OANDATMS-MT5",
        "123456",
        "123456",
        "DEMO",
        True,
        True,
        True,
        "EURUSD",
        True,
        2,
        "RECONCILED",
        False,
        0,
        0,
        9_000.0,
        0.0,
        0.0,
        0.00010,
        0.01,
        100.0,
        0.01,
        0.00001,
        5,
        10,
        0.00001,
        1.0,
    )
    return replace(value, **changes)


def dry_gate() -> dict[str, object]:
    return {
        "status": "DRY_RUN_READY",
        "order_check_allowed": True,
        "order_send_allowed": False,
        "demo_execution_enabled": False,
        "account_is_demo": True,
        "risk_approved": True,
        "reconciliation_ok": True,
        "execution_allowed": False,
        "real_trading": False,
    }


def canary_gate() -> dict[str, object]:
    return {
        **dry_gate(),
        "status": "CANARY_READY",
        "order_send_allowed": True,
        "demo_execution_enabled": True,
    }


def risk() -> dict[str, object]:
    return {"status": "ALLOW_DEMO", "risk_approved": True, "real_trading": False}


def reservation() -> dict[str, object]:
    return {
        "status": "RESERVED",
        "reserved": True,
        "proposal_hash": hashlib.sha256(proposal().proposal_id.encode()).hexdigest(),
    }


def authorization() -> CanaryAuthorization:
    return CanaryAuthorization(
        proposal_id=proposal().proposal_id,
        account_fingerprint=account_fingerprint(evidence()),
        issued_at_utc=(NOW - timedelta(seconds=1)).isoformat(),
        expires_at_utc=(NOW + timedelta(seconds=30)).isoformat(),
        single_use=True,
        consumed=False,
    )


def test_order_check_uses_live_demo_identity_and_never_sends() -> None:
    mt5 = FakeMT5()
    result = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    assert result["status"] == "ORDER_CHECKED"
    assert result["accepted"] is True
    assert mt5.check_calls == 1
    assert mt5.send_calls == 0
    assert result["real_trading"] is False


def test_live_real_or_changed_identity_hard_blocks_before_order_check() -> None:
    for account_change, terminal_change in (
        ({"trade_mode": 2}, {}),
        ({"server": "Unexpected"}, {}),
        ({}, {"path": r"C:\Other\terminal64.exe"}),
    ):
        mt5 = FakeMT5()
        mt5.account.update(account_change)
        mt5.terminal.update(terminal_change)
        result = perform_order_check(mt5, proposal(), evidence(), dry_gate())
        assert result["status"] == "HARD_BLOCK"
        assert mt5.check_calls == 0
        assert mt5.send_calls == 0


def test_order_check_classifies_rejection_and_unknown_result_without_retry() -> None:
    mt5 = FakeMT5()
    mt5.check_result = {"retcode": mt5.TRADE_RETCODE_INVALID_STOPS, "comment": "bad"}
    rejected = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    assert rejected["reason"] == "invalid_stops"
    assert rejected["retry_allowed"] is False
    mt5.check_result = None
    missing = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    assert missing["reason"] == "order_check_no_result"
    assert mt5.check_calls == 2
    assert mt5.send_calls == 0


def test_canary_adapter_refuses_missing_gate_or_check() -> None:
    mt5 = FakeMT5()
    result = submit_demo_canary(
        mt5, proposal(), evidence(), dry_gate(), {"status": "BLOCKED"}, reservation()
    )
    assert result["status"] == "BLOCKED"
    assert mt5.send_calls == 0


def test_synthetic_canary_calls_fake_send_once_and_requires_reconciliation() -> None:
    mt5 = FakeMT5()
    checked = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    result = submit_demo_canary(
        mt5, proposal(), evidence(), canary_gate(), checked, reservation()
    )
    assert result["status"] == "FILLED"
    assert result["requires_reconciliation"] is True
    assert result["retry_allowed"] is False
    assert result["real_trading"] is False
    assert mt5.send_calls == 1


def test_canary_adapter_requires_atomic_reservation() -> None:
    mt5 = FakeMT5()
    checked = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    result = submit_demo_canary(
        mt5,
        proposal(),
        evidence(),
        canary_gate(),
        checked,
        {"status": "DUPLICATE", "reserved": False},
    )
    assert result["status"] == "BLOCKED"
    assert "submission_not_atomically_reserved" in result["reason_codes"]
    assert mt5.send_calls == 0


def test_broker_execution_state_is_read_only_and_identity_guarded() -> None:
    mt5 = FakeMT5()
    mt5.positions = [{"ticket": 1, "symbol": "EURUSD", "volume": 0.01, "password": "hidden"}]
    result = read_broker_execution_state(mt5, evidence())
    assert result["status"] == "OK"
    assert result["positions"][0]["ticket"] == 1
    assert "password" not in result["positions"][0]
    mt5.account["trade_mode"] = 2
    assert read_broker_execution_state(mt5, evidence())["status"] == "HARD_BLOCK"


def test_execution_ledger_is_hash_chained_linked_and_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    first = append_execution_event(
        path=path,
        proposal=proposal(),
        evidence=evidence(),
        risk_result=risk(),
        execution_status="PROPOSED",
        reconciliation_status="RECONCILED",
    )
    append_execution_event(
        path=path,
        proposal=proposal(),
        evidence=evidence(),
        risk_result=risk(),
        execution_status="ORDER_CHECKED",
        reconciliation_status="RECONCILED",
        order_check_result={"retcode": 0},
    )
    state = read_execution_ledger(path)
    assert state["status"] == "OK"
    assert state["records_count"] == 2
    assert first["decision_id"] == "decision-1"
    assert first["execution_allowed_scope"] == "DEMO"
    reserved = reserve_submission(path, "proposal-1")
    duplicate = reserve_submission(path, "proposal-1")
    assert reserved["reserved"] is True
    assert duplicate["status"] == "DUPLICATE"
    assert submission_already_attempted(path, "proposal-1") is True


def test_execution_ledger_detects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    append_execution_event(
        path=path,
        proposal=proposal(),
        evidence=evidence(),
        risk_result=risk(),
        execution_status="PROPOSED",
        reconciliation_status="RECONCILED",
    )
    record = json.loads(path.read_text())
    record["symbol"] = "GBPUSD"
    path.write_text(json.dumps(record) + "\n")
    assert read_execution_ledger(path)["status"] == "INVALID"


def test_recovery_uses_broker_truth_and_blocks_orphans_and_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    clean = recovery_gate(
        ledger_path=path, broker_positions=[], broker_orders=[], terminal_connected=True
    )
    assert clean["status"] == "RECONCILED"
    orphan = reconcile_broker_truth(
        ledger_path=path,
        broker_positions=[{"ticket": 99, "symbol": "EURUSD"}],
        broker_orders=[],
    )
    assert orphan["status"] == "RECONCILIATION_BLOCK"
    assert orphan["reason"] == "unexpected_broker_position"
    disconnected = recovery_gate(
        ledger_path=path, broker_positions=[], broker_orders=[], terminal_connected=False
    )
    assert disconnected["status"] == "RECONCILIATION_BLOCK"


def test_filled_position_reconciles_all_protection_fields(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    append_execution_event(
        path=path,
        proposal=proposal(),
        evidence=evidence(),
        risk_result=risk(),
        execution_status="FILLED",
        reconciliation_status="PENDING",
        executed_volume=0.01,
        executed_price=1.1,
        ticket=20,
        position_id=30,
    )
    position = {
        "ticket": 30,
        "symbol": "EURUSD",
        "volume": 0.01,
        "price_open": 1.1,
        "sl": 1.099,
        "tp": 1.102,
    }
    assert reconcile_broker_truth(
        ledger_path=path, broker_positions=[position], broker_orders=[]
    )["status"] == "RECONCILED"
    position["sl"] = 0.0
    mismatch = reconcile_broker_truth(
        ledger_path=path, broker_positions=[position], broker_orders=[]
    )
    assert mismatch["status"] == "RECONCILIATION_BLOCK"
    assert "stop_loss" in mismatch["details"]


def test_dry_run_service_checks_broker_and_never_sends(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    path = tmp_path / "execution.jsonl"
    result = run_demo_dry_run(
        mt5,
        proposal=proposal(),
        evidence=evidence(),
        risk_result=risk(),
        ledger_path=path,
        now_utc=NOW,
    )
    assert result["status"] == "DRY_RUN_VALIDATED"
    assert result["order_send_called"] is False
    assert mt5.check_calls == 1
    assert mt5.send_calls == 0
    ledger = read_execution_ledger(path)
    assert ledger["status"] == "OK"
    assert ledger["records_count"] == 3


def test_synthetic_canary_is_one_shot_and_stops_after_reconciliation(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    mt5.materialize_fill = True
    path = tmp_path / "execution.jsonl"
    result = run_demo_canary(
        mt5,
        proposal=proposal(),
        evidence=evidence(),
        risk_result=risk(),
        authorization=authorization(),
        ledger_path=path,
        now_utc=NOW,
    )
    assert result["status"] == "CANARY_SUBMITTED_AND_RECONCILED"
    assert result["new_executions_enabled"] is False
    assert mt5.send_calls == 1
    repeated = run_demo_canary(
        mt5,
        proposal=proposal(),
        evidence=evidence(),
        risk_result=risk(),
        authorization=authorization(),
        ledger_path=path,
        now_utc=NOW,
    )
    assert repeated["status"] == "BLOCKED"
    assert repeated["reason"] == "canary_already_attempted"
    assert mt5.send_calls == 1


def test_response_lost_requires_reconciliation_and_never_retries(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    mt5.send_result = None
    path = tmp_path / "execution.jsonl"
    result = run_demo_canary(
        mt5,
        proposal=proposal(),
        evidence=evidence(),
        risk_result=risk(),
        authorization=authorization(),
        ledger_path=path,
        now_utc=NOW,
    )
    assert result["status"] == "RECONCILIATION_BLOCK"
    assert mt5.send_calls == 1
    assert result["new_executions_enabled"] is False

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path

import pytest

from odin.trading import demo_execution_service
from odin.adapters.mt5.demo_execution_adapter import (
    perform_order_check,
    read_broker_execution_state,
    submit_autonomous_demo_order,
    submit_demo_canary,
)
from odin.contracts.demo_execution import (
    CanaryAuthorization,
    DemoAccountEvidence,
    DemoAutomationAuthorization,
    DemoRiskLimits,
    TradeProposal,
)
from odin.risk.demo_execution import evaluate_demo_risk
from odin.trading.demo_execution_gate import account_fingerprint, evaluate_demo_execution_gate
from odin.trading.demo_execution_service import (
    run_autonomous_demo_order,
    run_demo_canary,
    run_demo_dry_run,
)
from odin.trading.demo_reconciliation import reconcile_broker_truth, recovery_gate
from odin.trading.execution_ledger import (
    analyze_execution_ledger,
    append_execution_event,
    confirm_execution_reconciliation,
    read_execution_ledger,
    reserve_submission,
    submission_already_attempted,
)


NOW = datetime(2026, 8, 22, 12, tzinfo=UTC)


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
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
    SYMBOL_TRADE_MODE_DISABLED = 0
    SYMBOL_TRADE_EXECUTION_MARKET = 2

    def __init__(self) -> None:
        self.account = {
            "trade_mode": 0,
            "company": "OANDA TMS Brokers S.A.",
            "server": "OANDATMS-MT5",
            "login": 123456,
            "trade_allowed": True,
            "trade_expert": True,
        }
        self.terminal = {
            "path": r"D:\ODIN_LOCAL\mt5\terminal64.exe",
            "connected": True,
            "trade_allowed": True,
            "tradeapi_disabled": False,
        }
        self.symbol = {
            "name": "EURUSD.pro",
            "point": 0.00001,
            "filling_mode": 1,
            "trade_exemode": self.SYMBOL_TRADE_EXECUTION_MARKET,
            "trade_mode": 4,
        }
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
        return self.symbol if symbol == "EURUSD.pro" else None

    def symbol_info_tick(self, symbol: str) -> object:
        return self.tick if symbol == "EURUSD.pro" else None

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
                    "type": request["type"],
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
        "EURUSD.pro",
        "EURUSD.pro",
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
        "execution_allowed_scope": "DEMO_CANARY_ONE_SHOT",
    }


def rc2_limits() -> DemoRiskLimits:
    return DemoRiskLimits(
        max_risk_per_trade=5.0,
        max_daily_demo_loss=5.0,
        max_completed_trades_per_day=3,
    )


def automation_authorization() -> DemoAutomationAuthorization:
    return DemoAutomationAuthorization(
        authorization_id="human-authorized-rc2",
        account_fingerprint=account_fingerprint(evidence()),
        issued_at_utc=(NOW - timedelta(seconds=1)).isoformat(),
        strategy_id="trend_mean_v1",
        max_position_size=0.01,
        max_completed_trades_per_day=3,
        max_daily_demo_loss=5.0,
    )


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
    assert result["request"]["type_filling"] == mt5.ORDER_FILLING_FOK
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


@pytest.mark.parametrize(
    ("retcode_name", "reason"),
    [
        ("TRADE_RETCODE_REJECT", "order_rejected"),
        ("TRADE_RETCODE_INVALID_VOLUME", "invalid_volume"),
        ("TRADE_RETCODE_INVALID_STOPS", "invalid_stops"),
        ("TRADE_RETCODE_NO_MONEY", "insufficient_margin"),
        ("TRADE_RETCODE_MARKET_CLOSED", "market_closed"),
        ("TRADE_RETCODE_REQUOTE", "requote"),
        ("TRADE_RETCODE_PRICE_CHANGED", "price_changed"),
        ("TRADE_RETCODE_TIMEOUT", "timeout"),
        ("TRADE_RETCODE_INVALID_FILL", "filling_mode_error"),
    ],
)
def test_order_check_classifies_all_known_mt5_failures_once(
    retcode_name: str, reason: str
) -> None:
    mt5 = FakeMT5()
    mt5.check_result = {"retcode": getattr(mt5, retcode_name), "comment": "fixture"}

    result = perform_order_check(mt5, proposal(), evidence(), dry_gate())

    assert result["status"] == "BLOCKED"
    assert result["reason"] == reason
    assert result["retry_allowed"] is False
    assert mt5.check_calls == 1
    assert mt5.send_calls == 0


def test_bad_price_and_filling_mode_block_before_order_check() -> None:
    mt5 = FakeMT5()
    mt5.tick["ask"] = 0.0
    bad_price = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    assert bad_price["reason"] == "bad_price"
    assert mt5.check_calls == 0

    mt5.tick["ask"] = 1.10000
    mt5.symbol["filling_mode"] = None
    bad_filling = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    assert bad_filling["reason"] == "filling_mode_error"
    assert mt5.check_calls == 0
    assert mt5.send_calls == 0


@pytest.mark.parametrize(
    ("symbol_flags", "execution_mode", "expected_order_mode"),
    [
        (1, 2, FakeMT5.ORDER_FILLING_FOK),
        (2, 2, FakeMT5.ORDER_FILLING_IOC),
        (3, 2, FakeMT5.ORDER_FILLING_FOK),
        (0, 1, FakeMT5.ORDER_FILLING_RETURN),
    ],
)
def test_symbol_filling_flags_are_mapped_to_order_filling_enum(
    symbol_flags: int, execution_mode: int, expected_order_mode: int
) -> None:
    mt5 = FakeMT5()
    mt5.symbol["filling_mode"] = symbol_flags
    mt5.symbol["trade_exemode"] = execution_mode

    result = perform_order_check(mt5, proposal(), evidence(), dry_gate())

    assert result["status"] == "ORDER_CHECKED"
    assert result["request"]["type_filling"] == expected_order_mode
    assert mt5.check_calls == 1
    assert mt5.send_calls == 0


def test_market_execution_without_documented_filling_flag_blocks() -> None:
    mt5 = FakeMT5()
    mt5.symbol["filling_mode"] = 0

    result = perform_order_check(mt5, proposal(), evidence(), dry_gate())

    assert result["status"] == "BLOCKED"
    assert result["reason"] == "filling_mode_error"
    assert mt5.check_calls == 0
    assert mt5.send_calls == 0


def test_disconnect_then_reconnect_requires_fresh_identity_check() -> None:
    mt5 = FakeMT5()
    mt5.terminal["connected"] = False
    disconnected = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    assert disconnected["status"] == "HARD_BLOCK"
    assert "live_terminal_disconnected" in disconnected["reason_codes"]
    assert mt5.check_calls == 0

    mt5.terminal["connected"] = True
    reconnected = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    assert reconnected["status"] == "ORDER_CHECKED"
    assert mt5.check_calls == 1
    assert mt5.send_calls == 0


def test_terminal_trade_permission_is_independent_and_blocks_until_enabled() -> None:
    mt5 = FakeMT5()
    mt5.terminal["trade_allowed"] = False

    blocked = perform_order_check(mt5, proposal(), evidence(), dry_gate())

    assert blocked["status"] == "HARD_BLOCK"
    assert "live_terminal_trading_not_allowed" in blocked["reason_codes"]
    assert mt5.check_calls == 0
    assert mt5.send_calls == 0

    mt5.terminal["trade_allowed"] = True
    allowed = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    assert allowed["status"] == "ORDER_CHECKED"
    assert mt5.check_calls == 1
    assert mt5.send_calls == 0


def test_canary_adapter_refuses_missing_gate_or_check() -> None:
    mt5 = FakeMT5()
    result = submit_demo_canary(
        mt5, proposal(), evidence(), dry_gate(), {"status": "BLOCKED"}, reservation()
    )
    assert result["status"] == "BLOCKED"
    assert result["order_send_called"] is False
    assert mt5.send_calls == 0


def test_synthetic_canary_calls_fake_send_once_and_requires_reconciliation() -> None:
    mt5 = FakeMT5()
    checked = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    result = submit_demo_canary(
        mt5, proposal(), evidence(), canary_gate(), checked, reservation()
    )
    assert result["status"] == "FILLED"
    assert result["requires_reconciliation"] is True
    assert result["order_send_called"] is True
    assert result["retry_allowed"] is False
    assert result["real_trading"] is False
    assert mt5.send_calls == 1


def test_rc2_authorization_is_account_bound_and_keeps_global_flags_false() -> None:
    prop = proposal()
    ev = evidence()
    result = evaluate_demo_execution_gate(
        prop,
        ev,
        evaluate_demo_risk(prop, ev, limits=rc2_limits()),
        duplicate_detected=False,
        limits=rc2_limits(),
        automation_authorization=automation_authorization(),
        now_utc=NOW,
    )

    assert result["status"] == "AUTONOMOUS_DEMO_READY"
    assert result["execution_allowed_scope"] == "ODIN_AUTONOMOUS_DEMO_RC2"
    assert result["order_send_allowed"] is True
    assert result["execution_allowed"] is False
    assert result["safe_to_trade"] is False
    assert result["real_trading"] is False


@pytest.mark.parametrize(
    ("ev_changes", "reason"),
    [
        ({"account_mode": "REAL"}, "account_not_proven_demo"),
        ({"account_mode": "UNKNOWN"}, "account_not_proven_demo"),
        ({"server": "WRONG"}, "server_identity_mismatch"),
        ({"completed_trades_today": 3}, "daily_completed_trade_limit"),
        ({"daily_realized_pnl": -5.0}, "risk_not_allow_demo"),
    ],
)
def test_rc2_gate_fails_closed_before_submission(
    ev_changes: dict[str, object], reason: str
) -> None:
    prop = proposal()
    ev = evidence(**ev_changes)
    result = evaluate_demo_execution_gate(
        prop,
        ev,
        evaluate_demo_risk(prop, ev, limits=rc2_limits()),
        duplicate_detected=False,
        limits=rc2_limits(),
        automation_authorization=automation_authorization(),
        now_utc=NOW,
    )

    assert result["status"] in {"HARD_BLOCK", "BLOCK"}
    assert reason in result["reason_codes"]
    assert result["order_send_allowed"] is False


def test_rc2_adapter_requires_rc2_scope_and_submits_fake_once() -> None:
    mt5 = FakeMT5()
    prop = proposal()
    ev = evidence()
    gate = evaluate_demo_execution_gate(
        prop,
        ev,
        evaluate_demo_risk(prop, ev, limits=rc2_limits()),
        duplicate_detected=False,
        limits=rc2_limits(),
        automation_authorization=automation_authorization(),
        now_utc=NOW,
    )
    checked = perform_order_check(mt5, prop, ev, gate, limits=rc2_limits())

    result = submit_autonomous_demo_order(
        mt5, prop, ev, gate, checked, reservation()
    )

    assert checked["request"]["comment"].startswith("ODIN_RC2_")
    assert result["status"] == "FILLED"
    assert result["execution_allowed_scope"] == "ODIN_AUTONOMOUS_DEMO_RC2"
    assert mt5.send_calls == 1


def test_rc2_service_reconciles_one_fake_order_without_canary_marker(
    tmp_path: Path,
) -> None:
    mt5 = FakeMT5()
    mt5.materialize_fill = True
    path = tmp_path / "execution.jsonl"
    result = run_autonomous_demo_order(
        mt5,
        proposal=proposal(),
        evidence=evidence(),
        risk_result=evaluate_demo_risk(proposal(), evidence(), limits=rc2_limits()),
        authorization=automation_authorization(),
        ledger_path=path,
        limits=rc2_limits(),
        now_utc=NOW,
    )

    assert result["status"] == "AUTONOMOUS_DEMO_SUBMITTED_AND_RECONCILED"
    assert result["order_send_called"] is True
    assert mt5.send_calls == 1
    assert not (tmp_path / ".demo_canary_attempted.json").exists()


def test_synthetic_canary_rejection_is_classified_without_retry() -> None:
    mt5 = FakeMT5()
    mt5.send_result = {
        "retcode": mt5.TRADE_RETCODE_NO_MONEY,
        "comment": "fixture",
    }
    checked = perform_order_check(mt5, proposal(), evidence(), dry_gate())

    result = submit_demo_canary(
        mt5, proposal(), evidence(), canary_gate(), checked, reservation()
    )

    assert result["status"] == "REJECTED"
    assert result["reason"] == "insufficient_margin"
    assert result["order_send_called"] is True
    assert result["retry_allowed"] is False
    assert result["requires_reconciliation"] is True
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
    assert result["order_send_called"] is False
    assert mt5.send_calls == 0


def test_identity_change_after_check_blocks_before_submission() -> None:
    mt5 = FakeMT5()
    checked = perform_order_check(mt5, proposal(), evidence(), dry_gate())
    mt5.account["trade_mode"] = 2

    result = submit_demo_canary(
        mt5, proposal(), evidence(), canary_gate(), checked, reservation()
    )

    assert result["status"] == "HARD_BLOCK"
    assert result["order_send_called"] is False
    assert mt5.send_calls == 0


def test_broker_execution_state_is_read_only_and_identity_guarded() -> None:
    mt5 = FakeMT5()
    mt5.positions = [
        {"ticket": 1, "symbol": "EURUSD.pro", "volume": 0.01, "password": "hidden"}
    ]
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
        broker_positions=[{"ticket": 99, "symbol": "EURUSD.pro"}],
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
        "symbol": "EURUSD.pro",
        "type": 0,
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

    position["sl"] = 1.099
    position["type"] = 1
    wrong_side = reconcile_broker_truth(
        ledger_path=path, broker_positions=[position], broker_orders=[]
    )
    assert wrong_side["status"] == "RECONCILIATION_BLOCK"
    assert "side" in wrong_side["details"]


def test_restart_after_submit_reconciles_broker_order_before_new_work(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    append_execution_event(
        path=path,
        proposal=proposal(),
        evidence=evidence(),
        risk_result=risk(),
        execution_status="SUBMITTED",
        reconciliation_status="PENDING",
        ticket=20,
    )
    broker_order = {
        "ticket": 20,
        "symbol": "EURUSD.pro",
        "type": 0,
        "sl": 1.099,
        "tp": 1.102,
    }

    recovered = recovery_gate(
        ledger_path=path,
        broker_positions=[],
        broker_orders=[broker_order],
        terminal_connected=True,
    )

    assert recovered["status"] == "RECONCILED"
    assert recovered["recovery_completed"] is True
    assert recovered["broker_is_source_of_truth"] is True


def test_incomplete_ledger_blocks_restart_recovery(tmp_path: Path) -> None:
    path = tmp_path / "execution.jsonl"
    path.write_text('{"sequence":', encoding="utf-8")

    result = recovery_gate(
        ledger_path=path,
        broker_positions=[],
        broker_orders=[],
        terminal_connected=True,
    )

    assert result["status"] == "RECONCILIATION_BLOCK"
    assert result["reason"] == "execution_ledger_invalid"


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


def test_dry_run_service_blocks_risk_before_order_check(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    result = run_demo_dry_run(
        mt5,
        proposal=proposal(),
        evidence=evidence(),
        risk_result={"status": "BLOCK", "risk_approved": False},
        ledger_path=tmp_path / "execution.jsonl",
        now_utc=NOW,
    )

    assert result["status"] == "BLOCKED"
    assert result["reason"] == "demo_gate_blocked"
    assert mt5.check_calls == 0
    assert mt5.send_calls == 0


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
    assert result["order_send_called"] is True
    assert result["new_executions_enabled"] is False
    assert mt5.send_calls == 1
    ledger = read_execution_ledger(path)
    assert ledger["status"] == "OK"
    assert ledger["records_count"] == 3
    assert ledger["latest"]["execution_status"] == "RECONCILED"
    assert ledger["latest"]["reconciliation_status"] == "RECONCILED"
    assert ledger["latest"]["position_id"] == 30
    assert analyze_execution_ledger(path)["status"] == "OK"
    already = confirm_execution_reconciliation(
        path=path,
        proposal_id=proposal().proposal_id,
        reconciliation_result=result["reconciliation"],
    )
    assert already["status"] == "ALREADY_RECONCILED"
    assert already["appended"] is False
    assert read_execution_ledger(path)["records_count"] == 3
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
    assert result["order_send_called"] is True
    assert mt5.send_calls == 1
    assert result["new_executions_enabled"] is False


def test_submission_boundary_block_consumes_one_shot_without_false_call_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mt5 = FakeMT5()
    path = tmp_path / "execution.jsonl"

    def blocked_submission(*args: object, **kwargs: object) -> dict[str, object]:
        return {
            "status": "HARD_BLOCK",
            "reason": "identity_changed",
            "order_send_called": False,
        }

    monkeypatch.setattr(
        demo_execution_service, "submit_demo_canary", blocked_submission
    )
    result = run_demo_canary(
        mt5,
        proposal=proposal(),
        evidence=evidence(),
        risk_result=risk(),
        authorization=authorization(),
        ledger_path=path,
        now_utc=NOW,
    )

    assert result["status"] == "BLOCKED"
    assert result["reason"] == "broker_submission_blocked"
    assert result["canary_attempt_consumed"] is True
    assert result["order_send_called"] is False
    assert (tmp_path / ".demo_canary_attempted.json").exists()
    assert mt5.send_calls == 0


def test_controlled_green_preflight_is_canary_ready_but_never_submits(tmp_path: Path) -> None:
    mt5 = FakeMT5()
    prop = proposal()
    ev = evidence(
        account_mode="DEMO",
        broker="OANDA TMS Brokers S.A.",
        server="OANDATMS-MT5",
        data_fresh=True,
        data_age_seconds=2,
        reconciliation_status="RECONCILED",
        kill_switch_engaged=False,
        spread=0.00010,
    )
    risk_result = evaluate_demo_risk(prop, ev)

    dry_run = run_demo_dry_run(
        mt5,
        proposal=prop,
        evidence=ev,
        risk_result=risk_result,
        ledger_path=tmp_path / "execution.jsonl",
        now_utc=NOW,
    )
    awaiting_human = evaluate_demo_execution_gate(
        prop,
        ev,
        risk_result,
        duplicate_detected=False,
        now_utc=NOW,
    )
    synthetic_canary_proof = evaluate_demo_execution_gate(
        prop,
        ev,
        risk_result,
        duplicate_detected=False,
        canary_authorization=authorization(),
        now_utc=NOW,
    )
    preflight = {
        "status": "CANARY READY — HUMAN CONFIRMATION REQUIRED",
        "broker_submission_called": mt5.send_calls > 0,
    }

    assert risk_result["status"] == "ALLOW_DEMO"
    assert dry_run["status"] == "DRY_RUN_VALIDATED"
    assert awaiting_human["status"] == "DRY_RUN_READY"
    assert awaiting_human["reason_codes"] == ["human_canary_confirmation_required"]
    assert synthetic_canary_proof["status"] == "CANARY_READY"
    assert preflight["status"] == "CANARY READY — HUMAN CONFIRMATION REQUIRED"
    assert preflight["broker_submission_called"] is False
    assert mt5.check_calls == 1
    assert mt5.send_calls == 0
    assert dry_run["real_trading"] is False


@pytest.mark.parametrize(
    ("ev_changes", "risk_override", "expected_status", "expected_reason"),
    [
        ({"account_mode": "REAL"}, None, "HARD_BLOCK", "account_not_proven_demo"),
        ({"account_mode": "UNKNOWN"}, None, "HARD_BLOCK", "account_not_proven_demo"),
        ({"server": "WRONG"}, None, "HARD_BLOCK", "server_identity_mismatch"),
        ({"data_fresh": False}, None, "BLOCK", "stale_data"),
        ({"spread": 0.00031}, None, "BLOCK", "risk_not_allow_demo"),
        (
            {"reconciliation_status": "MISMATCH"},
            None,
            "BLOCK",
            "reconciliation_not_ok",
        ),
        ({}, {"status": "BLOCK", "risk_approved": False}, "BLOCK", "risk_not_allow_demo"),
        ({"kill_switch_engaged": True}, None, "BLOCK", "kill_switch_engaged"),
    ],
)
def test_canary_preflight_block_matrix_never_reaches_broker_submission(
    ev_changes: dict[str, object],
    risk_override: dict[str, object] | None,
    expected_status: str,
    expected_reason: str,
) -> None:
    mt5 = FakeMT5()
    prop = proposal()
    ev = evidence(**ev_changes)
    risk_result = risk_override or evaluate_demo_risk(prop, ev)

    result = evaluate_demo_execution_gate(
        prop,
        ev,
        risk_result,
        duplicate_detected=False,
        now_utc=NOW,
    )

    assert result["status"] == expected_status
    assert expected_reason in result["reason_codes"]
    assert result["order_send_allowed"] is False
    assert result["real_trading"] is False
    assert mt5.send_calls == 0

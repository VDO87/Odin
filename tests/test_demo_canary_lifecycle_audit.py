import json

from odin.trading.demo_decision_ledger import (
    append_demo_decision,
    read_demo_decision_ledger,
)
from odin.trading.execution_ledger import (
    analyze_execution_ledger,
    append_execution_event,
    confirm_execution_close,
    confirm_execution_reconciliation,
    read_execution_ledger,
)

from test_demo_execution_gate import evidence, proposal


def _decision() -> dict[str, object]:
    return {
        "schema": "odin.demo_execution_decision/v1",
        "decision_id": "decision-1",
        "proposal_id": "proposal-1",
        "account_mode": "DEMO",
        "broker": "OANDA TMS Brokers S.A.",
        "server": "OANDATMS-MT5",
        "symbol": "EURUSD",
        "human_confirmation": "EXPLICIT_DEMO_CANARY_ONE_SHOT",
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _close_evidence() -> dict[str, object]:
    return {
        "status": "CLOSED",
        "broker_is_source_of_truth": True,
        "position_open": False,
        "pending_order": False,
        "position_id": 151407246,
        "volume": 0.01,
        "exit_price": 1.16335,
        "close_time_utc": "2026-08-28T14:01:42+00:00",
        "realized_pnl": -0.88,
        "close_reason": "SL",
        "close_order_id": 151427905,
        "close_deal_id": 105378769,
        "commission": 0.0,
        "swap": 0.0,
        "fee": 0.0,
        "exit_slippage_points": 2.0,
        "evidence_hash": "a" * 64,
    }


def test_demo_decision_ledger_is_hash_chained_and_idempotent(tmp_path) -> None:
    path = tmp_path / "demo_decision_ledger.jsonl"
    first = append_demo_decision(path=path, decision=_decision(), retrospective=True)
    second = append_demo_decision(path=path, decision=_decision(), retrospective=True)

    assert first["status"] == "RECORDED"
    assert first["appended"] is True
    assert second["status"] == "ALREADY_RECORDED"
    assert second["appended"] is False
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1
    assert read_demo_decision_ledger(path)["status"] == "OK"


def test_demo_decision_ledger_rejects_guardrail_drift_and_tampering(tmp_path) -> None:
    path = tmp_path / "demo_decision_ledger.jsonl"
    invalid = {**_decision(), "execution_allowed": True}
    assert append_demo_decision(path=path, decision=invalid)["status"] == "BLOCKED"

    append_demo_decision(path=path, decision=_decision())
    record = json.loads(path.read_text(encoding="utf-8"))
    record["decision"]["account_mode"] = "REAL"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    assert read_demo_decision_ledger(path)["status"] == "INVALID"


def test_execution_close_is_append_only_idempotent_and_reconciled(tmp_path) -> None:
    path = tmp_path / "execution.jsonl"
    trade = proposal(proposal_id="proposal-1", decision_id="decision-1")
    ev = evidence()
    risk = {"status": "ALLOW_DEMO", "risk_approved": True}
    append_execution_event(
        path=path,
        proposal=trade,
        evidence=ev,
        risk_result=risk,
        execution_status="FILLED",
        reconciliation_status="PENDING",
        executed_volume=0.01,
        executed_price=1.16437,
        ticket=151407246,
    )
    reconciled = confirm_execution_reconciliation(
        path=path,
        proposal_id="proposal-1",
        reconciliation_result={
            "status": "RECONCILED",
            "broker_is_source_of_truth": True,
        },
        position_id=151407246,
    )
    closed = confirm_execution_close(
        path=path,
        proposal_id="proposal-1",
        close_evidence=_close_evidence(),
    )
    repeated = confirm_execution_close(
        path=path,
        proposal_id="proposal-1",
        close_evidence=_close_evidence(),
    )

    assert reconciled["status"] == "RECONCILED"
    assert closed["status"] == "CLOSED"
    assert closed["appended"] is True
    assert repeated["status"] == "ALREADY_CLOSED"
    assert repeated["appended"] is False
    ledger = read_execution_ledger(path)
    assert ledger["status"] == "OK"
    latest = ledger["latest"]
    assert isinstance(latest, dict)
    assert latest["execution_status"] == "CLOSED"
    assert latest["reconciliation_status"] == "RECONCILED"
    assert latest["close_reason"] == "SL"
    assert latest["realized_pnl"] == -0.88
    assert analyze_execution_ledger(path)["realized_pnl"] == -0.88


def test_execution_close_fails_closed_without_broker_proof(tmp_path) -> None:
    path = tmp_path / "execution.jsonl"
    trade = proposal(proposal_id="proposal-1", decision_id="decision-1")
    append_execution_event(
        path=path,
        proposal=trade,
        evidence=evidence(),
        risk_result={"status": "ALLOW_DEMO", "risk_approved": True},
        execution_status="RECONCILED",
        reconciliation_status="RECONCILED",
        executed_volume=0.01,
        executed_price=1.16437,
        ticket=151407246,
        position_id=151407246,
    )
    invalid = {**_close_evidence(), "position_open": True}
    result = confirm_execution_close(
        path=path,
        proposal_id="proposal-1",
        close_evidence=invalid,
    )
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "broker_close_not_proven"
    assert read_execution_ledger(path)["records_count"] == 1

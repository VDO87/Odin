"""Bounded orchestration for DEMO dry-run and one future human-gated CANARY."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any

from odin.adapters.mt5.demo_execution_adapter import (
    perform_order_check,
    read_broker_execution_state,
    submit_demo_canary,
)
from odin.contracts.demo_execution import (
    CanaryAuthorization,
    DemoAccountEvidence,
    DemoRiskLimits,
    TradeProposal,
)
from odin.trading.demo_execution_gate import evaluate_demo_execution_gate
from odin.trading.demo_reconciliation import recovery_gate
from odin.trading.execution_ledger import (
    append_execution_event,
    confirm_execution_reconciliation,
    reserve_submission,
    submission_already_attempted,
)


def run_demo_dry_run(
    mt5: Any,
    *,
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    risk_result: dict[str, object],
    ledger_path: str | Path,
    limits: DemoRiskLimits | None = None,
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Reconcile, gate and order-check once; never submit."""
    policy = limits or DemoRiskLimits()
    snapshot = read_broker_execution_state(mt5, evidence)
    if snapshot["status"] != "OK":
        return _service_block("broker_snapshot_blocked", snapshot)
    positions = snapshot.get("positions")
    orders = snapshot.get("orders")
    assert isinstance(positions, list) and isinstance(orders, list)
    recovery = recovery_gate(
        ledger_path=ledger_path,
        broker_positions=positions,
        broker_orders=orders,
        terminal_connected=True,
    )
    if recovery["status"] != "RECONCILED":
        return _service_block("recovery_not_reconciled", recovery)
    duplicate = submission_already_attempted(ledger_path, proposal.proposal_id)
    gate = evaluate_demo_execution_gate(
        proposal,
        evidence,
        risk_result,
        duplicate_detected=duplicate,
        limits=policy,
        now_utc=now_utc,
    )
    if gate["status"] != "DRY_RUN_READY":
        return _service_block("demo_gate_blocked", gate)
    append_execution_event(
        path=ledger_path,
        proposal=proposal,
        evidence=evidence,
        risk_result=risk_result,
        execution_status="PROPOSED",
        reconciliation_status="RECONCILED",
    )
    append_execution_event(
        path=ledger_path,
        proposal=proposal,
        evidence=evidence,
        risk_result=risk_result,
        execution_status="RISK_APPROVED",
        reconciliation_status="RECONCILED",
    )
    checked = perform_order_check(mt5, proposal, evidence, gate, limits=policy)
    if checked["status"] != "ORDER_CHECKED":
        append_execution_event(
            path=ledger_path,
            proposal=proposal,
            evidence=evidence,
            risk_result=risk_result,
            execution_status="REJECTED",
            reconciliation_status="RECONCILED",
            order_check_result=_dict_or_none(checked.get("order_check_result")),
        )
        return _service_block("order_check_blocked", checked)
    append_execution_event(
        path=ledger_path,
        proposal=proposal,
        evidence=evidence,
        risk_result=risk_result,
        execution_status="ORDER_CHECKED",
        reconciliation_status="RECONCILED",
        order_check_result=_dict_or_none(checked.get("order_check_result")),
    )
    return {
        "status": "DRY_RUN_VALIDATED",
        "proposal_id": proposal.proposal_id,
        "gate": gate,
        "order_check": checked,
        "order_send_called": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def run_demo_canary(
    mt5: Any,
    *,
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    risk_result: dict[str, object],
    authorization: CanaryAuthorization,
    ledger_path: str | Path,
    limits: DemoRiskLimits | None = None,
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Execute one future CANARY; caller must have explicit human confirmation."""
    policy = limits or DemoRiskLimits()
    if _canary_attempt_path(Path(ledger_path)).exists():
        return _service_block("canary_already_attempted")
    snapshot = read_broker_execution_state(mt5, evidence)
    if snapshot["status"] != "OK":
        return _service_block("broker_snapshot_blocked", snapshot)
    positions = snapshot.get("positions")
    orders = snapshot.get("orders")
    assert isinstance(positions, list) and isinstance(orders, list)
    recovery = recovery_gate(
        ledger_path=ledger_path,
        broker_positions=positions,
        broker_orders=orders,
        terminal_connected=True,
    )
    if recovery["status"] != "RECONCILED":
        return _service_block("recovery_not_reconciled", recovery)
    duplicate = submission_already_attempted(ledger_path, proposal.proposal_id)
    gate = evaluate_demo_execution_gate(
        proposal,
        evidence,
        risk_result,
        duplicate_detected=duplicate,
        limits=policy,
        canary_authorization=authorization,
        now_utc=now_utc,
    )
    if gate["status"] != "CANARY_READY":
        return _service_block("demo_gate_not_canary_ready", gate)
    checked = perform_order_check(mt5, proposal, evidence, gate, limits=policy)
    if checked["status"] != "ORDER_CHECKED":
        return _service_block("order_check_blocked", checked)
    reservation = reserve_submission(ledger_path, proposal.proposal_id)
    if reservation["status"] != "RESERVED":
        return _service_block("duplicate_submission_reservation", reservation)
    if not _reserve_canary_attempt(Path(ledger_path), proposal.proposal_id):
        return _service_block("canary_already_attempted")
    append_execution_event(
        path=ledger_path,
        proposal=proposal,
        evidence=evidence,
        risk_result=risk_result,
        execution_status="ORDER_CHECKED",
        reconciliation_status="RECONCILED",
        order_check_result=_dict_or_none(checked.get("order_check_result")),
    )
    submitted = submit_demo_canary(
        mt5, proposal, evidence, gate, checked, reservation
    )
    order_send_called = submitted.get("order_send_called") is True
    if not order_send_called:
        return {
            **_service_block("broker_submission_blocked", submitted),
            "canary_attempt_consumed": True,
        }
    broker_result = _dict_or_none(submitted.get("order_send_result"))
    attempted_status = str(submitted.get("status"))
    ledger_status = attempted_status if attempted_status in {"FILLED", "SUBMITTED", "REJECTED"} else "SUBMITTED"
    append_execution_event(
        path=ledger_path,
        proposal=proposal,
        evidence=evidence,
        risk_result=risk_result,
        execution_status=ledger_status,
        reconciliation_status="PENDING",
        order_check_result=_dict_or_none(checked.get("order_check_result")),
        order_send_result=broker_result,
        executed_volume=_number(broker_result, "volume"),
        executed_price=_number(broker_result, "price"),
        ticket=_integer(broker_result, "order"),
    )
    after = read_broker_execution_state(mt5, evidence)
    if after["status"] != "OK":
        return _reconciliation_block(
            "post_submit_snapshot_unavailable", submitted, order_send_called=True
        )
    after_positions = after.get("positions")
    after_orders = after.get("orders")
    assert isinstance(after_positions, list) and isinstance(after_orders, list)
    reconciled = recovery_gate(
        ledger_path=ledger_path,
        broker_positions=after_positions,
        broker_orders=after_orders,
        terminal_connected=True,
    )
    if reconciled["status"] != "RECONCILED":
        append_execution_event(
            path=ledger_path,
            proposal=proposal,
            evidence=evidence,
            risk_result=risk_result,
            execution_status="RECONCILIATION_BLOCK",
            reconciliation_status="RECONCILIATION_BLOCK",
            order_check_result=_dict_or_none(checked.get("order_check_result")),
            order_send_result=broker_result,
        )
        return _reconciliation_block(
            str(reconciled.get("reason")), submitted, order_send_called=True
        )
    position_id = None
    if len(after_positions) == 1:
        position_id = _integer(after_positions[0], "identifier") or _integer(
            after_positions[0], "ticket"
        )
    ledger_reconciliation = confirm_execution_reconciliation(
        path=ledger_path,
        proposal_id=proposal.proposal_id,
        reconciliation_result=reconciled,
        position_id=position_id,
    )
    if ledger_reconciliation["status"] not in {
        "RECONCILED",
        "ALREADY_RECONCILED",
    }:
        return _reconciliation_block(
            "ledger_reconciliation_persistence_failed",
            submitted,
            order_send_called=True,
        )
    return {
        "status": "CANARY_SUBMITTED_AND_RECONCILED",
        "submission": submitted,
        "reconciliation": reconciled,
        "ledger_reconciliation": ledger_reconciliation,
        "order_send_called": True,
        "new_executions_enabled": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _reserve_canary_attempt(ledger_path: Path, proposal_id: str) -> bool:
    path = _canary_attempt_path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"proposal_id": proposal_id, "state": "CANARY_ATTEMPTED"}))
    return True


def _canary_attempt_path(ledger_path: Path) -> Path:
    return ledger_path.parent / ".demo_canary_attempted.json"


def _service_block(reason: str, evidence: object | None = None) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "reason": reason,
        "evidence": evidence,
        "order_send_called": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _reconciliation_block(
    reason: str,
    submission: dict[str, object],
    *,
    order_send_called: bool,
) -> dict[str, object]:
    return {
        "status": "RECONCILIATION_BLOCK",
        "reason": reason,
        "submission": submission,
        "order_send_called": order_send_called,
        "new_executions_enabled": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _dict_or_none(value: object) -> dict[str, object] | None:
    return value if isinstance(value, dict) else None


def _number(value: dict[str, object] | None, key: str) -> float | None:
    item = value.get(key) if value else None
    return float(item) if isinstance(item, (int, float)) else None


def _integer(value: dict[str, object] | None, key: str) -> int | None:
    item = value.get(key) if value else None
    return int(item) if isinstance(item, (int, float)) else None

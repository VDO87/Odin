"""Append-only, hash-chained Execution Ledger linked to Shadow decisions."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path

from odin.contracts.demo_execution import DemoAccountEvidence, TradeProposal
from odin.contracts.events import redact_for_audit
from odin.shadow.ledger import current_commit


EXECUTION_STATES = {
    "PROPOSED",
    "RISK_APPROVED",
    "ORDER_CHECKED",
    "SUBMITTED",
    "FILLED",
    "REJECTED",
    "CANCELLED",
    "CLOSED",
    "RECONCILED",
    "RECONCILIATION_BLOCK",
}
_SUBMISSION_STATES = {"SUBMITTED", "FILLED", "REJECTED", "CANCELLED", "CLOSED"}
_ATTEMPT_RECORD_STATES = {"SUBMITTED", "FILLED", "REJECTED"}


def append_execution_event(
    *,
    path: str | Path,
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    risk_result: dict[str, object],
    execution_status: str,
    reconciliation_status: str,
    order_check_result: dict[str, object] | None = None,
    order_send_result: dict[str, object] | None = None,
    executed_volume: float | None = None,
    executed_price: float | None = None,
    ticket: int | None = None,
    position_id: int | None = None,
    slippage: float | None = None,
    open_time: str | None = None,
    close_time: str | None = None,
    realized_pnl: float | None = None,
) -> dict[str, object]:
    if execution_status not in EXECUTION_STATES:
        raise ValueError("invalid_execution_status")
    target = Path(path)
    previous = _read_records(target)
    previous_hash = str(previous[-1].get("record_hash", "")) if previous else "GENESIS"
    record: dict[str, object] = {
        "schema": "odin.execution_ledger/v1",
        "sequence": len(previous) + 1,
        "previous_record_hash": previous_hash,
        "git_commit": current_commit(),
        "decision_id": proposal.decision_id,
        "proposal_id": proposal.proposal_id,
        "timestamp": proposal.timestamp_utc,
        "strategy_version": proposal.strategy_version,
        "market_data_hash": proposal.market_data_hash,
        "data_quality": proposal.data_quality,
        "freshness": proposal.freshness,
        "account_mode": "DEMO",
        "broker": evidence.broker,
        "server": evidence.server,
        "symbol": proposal.symbol,
        "broker_symbol": evidence.broker_symbol,
        "side": proposal.side,
        "requested_volume": proposal.volume,
        "executed_volume": executed_volume,
        "requested_price": proposal.entry_reference,
        "executed_price": executed_price,
        "spread": evidence.spread,
        "slippage": slippage,
        "stop_loss": proposal.stop_loss,
        "take_profit": proposal.take_profit,
        "order_check_result": order_check_result,
        "order_send_result": order_send_result,
        "ticket": ticket,
        "position_id": position_id,
        "risk_result": risk_result,
        "execution_status": execution_status,
        "reconciliation_status": reconciliation_status,
        "open_time": open_time,
        "close_time": close_time,
        "realized_pnl": realized_pnl,
        "execution_allowed_scope": "DEMO",
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }
    sanitized = redact_for_audit(record)
    sanitized["record_hash"] = _record_hash(sanitized)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(sanitized, sort_keys=True) + "\n")
    return sanitized


def read_execution_ledger(path: str | Path) -> dict[str, object]:
    records = _read_records(Path(path))
    previous = "GENESIS"
    for index, record in enumerate(records, start=1):
        supplied_hash = record.get("record_hash")
        unsigned = dict(record)
        unsigned.pop("record_hash", None)
        if (
            record.get("sequence") != index
            or record.get("previous_record_hash") != previous
            or supplied_hash != _record_hash(unsigned)
        ):
            return _ledger_status("INVALID", records, "execution_ledger_integrity_failed")
        previous = str(supplied_hash)
    return _ledger_status("OK", records, "")


def submission_already_attempted(path: str | Path, proposal_id: str) -> bool:
    records = _read_records(Path(path))
    return (
        any(
            record.get("proposal_id") == proposal_id
            and record.get("execution_status") in _SUBMISSION_STATES
            for record in records
        )
        or _reservation_path(Path(path), proposal_id).exists()
    )


def completed_reconciled_lifecycle(path: str | Path, decision_id: str) -> bool:
    """Prove that a specific DEMO decision reached a broker-reconciled close."""
    target = Path(path)
    if read_execution_ledger(target)["status"] != "OK":
        return False
    return any(
        record.get("decision_id") == decision_id
        and record.get("execution_status") == "CLOSED"
        and record.get("reconciliation_status") == "RECONCILED"
        for record in _read_records(target)
    )


def analyze_execution_ledger(path: str | Path) -> dict[str, object]:
    """Return bounded anomalies for dashboards/supervision; never mutate ledger."""
    ledger_path = Path(path)
    verified = read_execution_ledger(ledger_path)
    records = _read_records(ledger_path)
    anomalies: list[str] = []
    if verified["status"] != "OK":
        anomalies.append("ledger_integrity_mismatch")
    attempts: dict[str, int] = {}
    for record in records:
        proposal_id = str(record.get("proposal_id", ""))
        status = record.get("execution_status")
        if status in _ATTEMPT_RECORD_STATES:
            attempts[proposal_id] = attempts.get(proposal_id, 0) + 1
        risk = record.get("risk_result")
        if status in {"SUBMITTED", "FILLED"} and (
            not isinstance(risk, dict) or risk.get("risk_approved") is not True
        ):
            anomalies.append("execution_without_risk_approval")
        if status in {"SUBMITTED", "FILLED"} and record.get("freshness") != "FRESH":
            anomalies.append("execution_with_stale_data")
        if status in {"SUBMITTED", "FILLED"} and (
            record.get("stop_loss") is None or record.get("take_profit") is None
        ):
            anomalies.append("execution_without_sl_tp")
        if record.get("reconciliation_status") == "RECONCILIATION_BLOCK":
            anomalies.append("reconciliation_block")
        slippage = record.get("slippage")
        if isinstance(slippage, (int, float)) and abs(slippage) > 0.00020:
            anomalies.append("unexpected_slippage")
        if record.get("requested_volume") not in {None, 0.01}:
            anomalies.append("wrong_volume")
        order_check = record.get("order_check_result")
        if isinstance(order_check, dict):
            margin = order_check.get("margin")
            if isinstance(margin, (int, float)) and margin < 0:
                anomalies.append("margin_anomaly")
    if any(count > 1 for count in attempts.values()):
        anomalies.append("duplicate_submission")
    realized = 0.0
    for record in records:
        value = record.get("realized_pnl")
        if isinstance(value, (int, float)) and record.get("execution_status") == "CLOSED":
            realized += float(value)
    return {
        "status": "OK" if not anomalies else "DEGRADED",
        "anomalies": sorted(set(anomalies)),
        "records_count": len(records),
        "submission_attempts": sum(attempts.values()),
        "realized_pnl": round(realized, 2),
        "latest": records[-1] if records else None,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def reserve_submission(path: str | Path, proposal_id: str) -> dict[str, object]:
    """Atomically reserve one proposal before broker contact; never auto-release."""
    ledger_path = Path(path)
    reservation = _reservation_path(ledger_path, proposal_id)
    reservation.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(proposal_id.encode()).hexdigest()
    try:
        descriptor = os.open(reservation, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return {"status": "DUPLICATE", "reserved": False, "proposal_hash": digest}
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"proposal_hash": digest, "state": "SUBMISSION_RESERVED"}))
    return {"status": "RESERVED", "reserved": True, "proposal_hash": digest}


def confirm_execution_reconciliation(
    *,
    path: str | Path,
    proposal_id: str,
    reconciliation_result: dict[str, object],
    position_id: int | None = None,
) -> dict[str, object]:
    """Append one idempotent final event after broker truth is reconciled."""
    target = Path(path)
    verified = read_execution_ledger(target)
    if verified["status"] != "OK":
        return _reconciliation_confirmation_block("execution_ledger_invalid")
    latest = verified.get("latest")
    if not isinstance(latest, dict) or latest.get("proposal_id") != proposal_id:
        return _reconciliation_confirmation_block("reconciliation_proposal_mismatch")
    already_reconciled = (
        latest.get("execution_status") == "RECONCILED"
        and latest.get("reconciliation_status") == "RECONCILED"
    )
    current_position_id = latest.get("position_id")
    if position_id is not None and position_id <= 0:
        return _reconciliation_confirmation_block("broker_position_id_invalid")
    if (
        already_reconciled
        and current_position_id is not None
        and position_id is not None
        and current_position_id != position_id
    ):
        return _reconciliation_confirmation_block("broker_position_id_mismatch")
    if already_reconciled and (position_id is None or current_position_id == position_id):
        return {
            "status": "ALREADY_RECONCILED",
            "appended": False,
            "record": latest,
            "execution_allowed": False,
            "safe_to_trade": False,
            "real_trading": False,
        }
    if not already_reconciled and (
        latest.get("execution_status") not in {"SUBMITTED", "FILLED"}
        or latest.get("reconciliation_status") != "PENDING"
    ):
        return _reconciliation_confirmation_block("execution_not_pending_reconciliation")
    if (
        reconciliation_result.get("status") != "RECONCILED"
        or reconciliation_result.get("broker_is_source_of_truth") is not True
    ):
        return _reconciliation_confirmation_block("broker_truth_not_reconciled")
    sequence = latest.get("sequence")
    if not isinstance(sequence, int):
        return _reconciliation_confirmation_block("execution_ledger_sequence_invalid")

    record = dict(latest)
    record.pop("record_hash", None)
    record.update(
        {
            "sequence": sequence + 1,
            "previous_record_hash": str(latest.get("record_hash", "")),
            "git_commit": current_commit(),
            "execution_status": "RECONCILED",
            "reconciliation_status": "RECONCILED",
            "reconciled_at_utc": datetime.now(UTC).isoformat(),
            "execution_allowed": False,
            "safe_to_trade": False,
            "real_trading": False,
        }
    )
    if position_id is not None:
        record["position_id"] = position_id
    sanitized = redact_for_audit(record)
    sanitized["record_hash"] = _record_hash(sanitized)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(sanitized, sort_keys=True) + "\n")
    return {
        "status": "RECONCILED",
        "appended": True,
        "record": sanitized,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def confirm_execution_close(
    *,
    path: str | Path,
    proposal_id: str,
    close_evidence: dict[str, object],
) -> dict[str, object]:
    """Append one idempotent CLOSED event after MT5 history proves the lifecycle."""
    target = Path(path)
    verified = read_execution_ledger(target)
    if verified["status"] != "OK":
        return _reconciliation_confirmation_block("execution_ledger_invalid")
    latest = verified.get("latest")
    if not isinstance(latest, dict) or latest.get("proposal_id") != proposal_id:
        return _reconciliation_confirmation_block("close_proposal_mismatch")

    position_id = close_evidence.get("position_id")
    if not isinstance(position_id, int) or position_id <= 0:
        return _reconciliation_confirmation_block("close_position_id_invalid")
    if latest.get("position_id") not in {None, position_id}:
        return _reconciliation_confirmation_block("close_position_id_mismatch")
    if latest.get("execution_status") == "CLOSED":
        if latest.get("position_id") != position_id:
            return _reconciliation_confirmation_block("closed_position_id_mismatch")
        return {
            "status": "ALREADY_CLOSED",
            "appended": False,
            "record": latest,
            "execution_allowed": False,
            "safe_to_trade": False,
            "real_trading": False,
        }
    if (
        latest.get("execution_status") != "RECONCILED"
        or latest.get("reconciliation_status") != "RECONCILED"
    ):
        return _reconciliation_confirmation_block("execution_not_open_reconciled")
    if (
        close_evidence.get("status") != "CLOSED"
        or close_evidence.get("broker_is_source_of_truth") is not True
        or close_evidence.get("position_open") is not False
        or close_evidence.get("pending_order") is not False
    ):
        return _reconciliation_confirmation_block("broker_close_not_proven")

    close_time = close_evidence.get("close_time_utc")
    close_reason = close_evidence.get("close_reason")
    exit_price = close_evidence.get("exit_price")
    realized_pnl = close_evidence.get("realized_pnl")
    closed_volume = close_evidence.get("volume")
    if not isinstance(close_time, str) or not close_time:
        return _reconciliation_confirmation_block("close_time_missing")
    try:
        parsed_close = datetime.fromisoformat(close_time)
    except ValueError:
        return _reconciliation_confirmation_block("close_time_invalid")
    if parsed_close.tzinfo is None or parsed_close.utcoffset() is None:
        return _reconciliation_confirmation_block("close_time_not_utc")
    if not isinstance(close_reason, str) or not close_reason:
        return _reconciliation_confirmation_block("close_reason_missing")
    if not isinstance(exit_price, (int, float)) or exit_price <= 0:
        return _reconciliation_confirmation_block("exit_price_invalid")
    if not isinstance(realized_pnl, (int, float)):
        return _reconciliation_confirmation_block("realized_pnl_missing")
    if not isinstance(closed_volume, (int, float)) or closed_volume != latest.get(
        "executed_volume"
    ):
        return _reconciliation_confirmation_block("closed_volume_mismatch")

    sequence = latest.get("sequence")
    if not isinstance(sequence, int):
        return _reconciliation_confirmation_block("execution_ledger_sequence_invalid")
    record = dict(latest)
    record.pop("record_hash", None)
    record.update(
        {
            "sequence": sequence + 1,
            "previous_record_hash": str(latest.get("record_hash", "")),
            "git_commit": current_commit(),
            "execution_status": "CLOSED",
            "reconciliation_status": "RECONCILED",
            "position_id": position_id,
            "close_time": parsed_close.astimezone(UTC).isoformat(),
            "exit_price": float(exit_price),
            "realized_pnl": float(realized_pnl),
            "close_reason": close_reason,
            "close_order_id": close_evidence.get("close_order_id"),
            "close_deal_id": close_evidence.get("close_deal_id"),
            "commission": close_evidence.get("commission"),
            "swap": close_evidence.get("swap"),
            "fee": close_evidence.get("fee"),
            "exit_slippage_points": close_evidence.get("exit_slippage_points"),
            "close_evidence_hash": close_evidence.get("evidence_hash"),
            "reconciled_at_utc": datetime.now(UTC).isoformat(),
            "execution_allowed": False,
            "safe_to_trade": False,
            "real_trading": False,
        }
    )
    sanitized = redact_for_audit(record)
    sanitized["record_hash"] = _record_hash(sanitized)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(sanitized, sort_keys=True) + "\n")
    return {
        "status": "CLOSED",
        "appended": True,
        "record": sanitized,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _reservation_path(ledger_path: Path, proposal_id: str) -> Path:
    name = hashlib.sha256(proposal_id.encode()).hexdigest()
    return ledger_path.parent / ".execution_reservations" / f"{name}.json"


def _reconciliation_confirmation_block(reason: str) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "reason": reason,
        "appended": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _read_records(path: Path) -> list[dict[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    records: list[dict[str, object]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            return [{"integrity_error": "invalid_json"}]
        if not isinstance(value, dict):
            return [{"integrity_error": "invalid_record"}]
        records.append(value)
    return records


def _record_hash(record: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _ledger_status(status: str, records: list[dict[str, object]], reason: str) -> dict[str, object]:
    return {
        "status": status,
        "reason": reason,
        "records_count": len(records),
        "latest": records[-1] if records else None,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }

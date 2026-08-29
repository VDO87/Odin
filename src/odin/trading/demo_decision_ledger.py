"""Append-only Decision Ledger for supervised DEMO execution decisions."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

from odin.contracts.events import redact_for_audit
from odin.shadow.ledger import current_commit


def append_demo_decision(
    *,
    path: str | Path,
    decision: dict[str, object],
    retrospective: bool = False,
) -> dict[str, object]:
    """Append one idempotent, non-authoritative-for-REAL DEMO decision."""
    target = Path(path)
    verified = read_demo_decision_ledger(target)
    if verified["status"] != "OK":
        return _blocked("demo_decision_ledger_integrity_failed")
    decision_id = decision.get("decision_id")
    proposal_id = decision.get("proposal_id")
    if not isinstance(decision_id, str) or not decision_id:
        return _blocked("demo_decision_id_missing")
    if not isinstance(proposal_id, str) or not proposal_id:
        return _blocked("demo_proposal_id_missing")
    if (
        decision.get("account_mode") != "DEMO"
        or decision.get("execution_allowed") is not False
        or decision.get("safe_to_trade") is not False
        or decision.get("real_trading") is not False
    ):
        return _blocked("demo_decision_guardrail_invalid")

    records = _read_records(target)
    for existing_record in records:
        existing = existing_record.get("decision")
        if not isinstance(existing, dict):
            continue
        if existing.get("decision_id") == decision_id:
            if existing.get("proposal_id") != proposal_id:
                return _blocked("demo_decision_proposal_mismatch")
            return {
                "status": "ALREADY_RECORDED",
                "appended": False,
                "record": existing_record,
                "execution_allowed": False,
                "safe_to_trade": False,
                "real_trading": False,
            }

    previous_hash = str(records[-1].get("record_hash", "")) if records else "GENESIS"
    record: dict[str, object] = {
        "schema": "odin.demo_decision_ledger/v1",
        "sequence": len(records) + 1,
        "previous_record_hash": previous_hash,
        "git_commit": current_commit(),
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "retrospective": retrospective,
        "decision": redact_for_audit(decision),
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }
    record["record_hash"] = _record_hash(record)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return {
        "status": "RECORDED",
        "appended": True,
        "record": record,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def read_demo_decision_ledger(path: str | Path) -> dict[str, object]:
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
            return _status("INVALID", records, "demo_decision_ledger_integrity_failed")
        previous = str(supplied_hash)
    return _status("OK", records, "")


def demo_decision_already_recorded(path: str | Path, decision_id: str) -> bool:
    """Return true only when the verified ledger already contains the decision."""
    target = Path(path)
    verified = read_demo_decision_ledger(target)
    if verified["status"] != "OK":
        return True
    for record in _read_records(target):
        decision = record.get("decision")
        if isinstance(decision, dict) and decision.get("decision_id") == decision_id:
            return True
    return False


def _read_records(path: Path) -> list[dict[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    except OSError:
        return [{"integrity_error": "read_failed"}]
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
    unsigned = dict(record)
    unsigned.pop("record_hash", None)
    return hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _status(status: str, records: list[dict[str, object]], reason: str) -> dict[str, object]:
    return {
        "status": status,
        "reason": reason,
        "records_count": len(records),
        "latest": records[-1] if records else None,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _blocked(reason: str) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "reason": reason,
        "appended": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }

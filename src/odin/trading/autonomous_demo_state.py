"""Durable, non-secret operational state for Autonomous DEMO RC2."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping


ALLOWED_STATES = frozenset(
    {
        "STARTING",
        "VALIDATING",
        "WAITING_MARKET",
        "MONITOR_ONLY",
        "READY_FOR_DECISION",
        "NO_TRADE",
        "PROPOSAL_CREATED",
        "RISK_CHECK",
        "ORDER_CHECK",
        "SUBMITTING_DEMO",
        "POSITION_OPEN",
        "POSITION_MONITOR",
        "RECONCILING",
        "TRADE_COMPLETE",
        "REPAIRING",
        "EXECUTION_PAUSED",
        "SECURITY_HARD_BLOCK",
        "DEGRADED",
        "RECOVERING",
        "ACCEPTANCE_PASSED",
    }
)
ALLOWED_CONTROLS = frozenset({"PAUSE", "RESUME", "SAFE_STOP"})
GLOBAL_GUARDRAILS = {
    "safe_to_trade": False,
    "real_trading": False,
    "execution_allowed": False,
}


def build_supervisor_state(
    state: str,
    *,
    cycle: int,
    reason_codes: list[str] | tuple[str, ...] = (),
    observed: Mapping[str, object] | None = None,
    branch: str = "",
    checkpoint: str = "",
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Build one sanitized state snapshot; financial global flags stay false."""
    if state not in ALLOWED_STATES:
        raise ValueError("autonomous_demo_state_invalid")
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    safe_observed = _sanitize_mapping(observed or {})
    payload: dict[str, object] = {
        "schema": "odin.autonomous_demo_state/v1",
        "mode": "ODIN_AUTONOMOUS_DEMO_RC2",
        "state": state,
        "cycle": max(0, int(cycle)),
        "reason_codes": [str(item) for item in reason_codes],
        "observed": safe_observed,
        "branch": branch,
        "checkpoint": checkpoint,
        "updated_at_utc": now.isoformat(),
        **GLOBAL_GUARDRAILS,
    }
    payload["content_hash"] = _content_hash(payload)
    return payload


def write_state(path: str | Path, state: Mapping[str, object]) -> None:
    """Atomically persist a previously built state snapshot."""
    target = Path(path)
    value = dict(state)
    if not validate_state(value):
        raise ValueError("autonomous_demo_state_integrity_failed")
    _atomic_json(target, value)


def read_state(path: str | Path) -> dict[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _blocked("autonomous_demo_state_missing")
    if not isinstance(value, dict) or not validate_state(value):
        return _blocked("autonomous_demo_state_integrity_failed")
    return value


def validate_state(value: Mapping[str, object]) -> bool:
    supplied = value.get("content_hash")
    unsigned = dict(value)
    unsigned.pop("content_hash", None)
    return (
        value.get("schema") == "odin.autonomous_demo_state/v1"
        and value.get("state") in ALLOWED_STATES
        and all(value.get(key) is expected for key, expected in GLOBAL_GUARDRAILS.items())
        and isinstance(supplied, str)
        and supplied == _content_hash(unsigned)
    )


def write_heartbeat(
    path: str | Path,
    *,
    cycle: int,
    state: str,
    process_id: int,
    started_at_utc: str,
    next_check_at_utc: str,
    now_utc: datetime | None = None,
) -> dict[str, object]:
    if state not in ALLOWED_STATES:
        raise ValueError("autonomous_demo_state_invalid")
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    payload: dict[str, object] = {
        "schema": "odin.autonomous_demo_heartbeat/v1",
        "mode": "ODIN_AUTONOMOUS_DEMO_RC2",
        "state": state,
        "cycle": max(0, int(cycle)),
        "process_id": max(0, int(process_id)),
        "started_at_utc": started_at_utc,
        "heartbeat_at_utc": now.isoformat(),
        "next_check_at_utc": next_check_at_utc,
        **GLOBAL_GUARDRAILS,
    }
    payload["content_hash"] = _content_hash(payload)
    _atomic_json(Path(path), payload)
    return payload


def append_incident(
    path: str | Path,
    *,
    incident_type: str,
    component: str,
    error_code: str,
    root_cause: str,
    evidence: Mapping[str, object],
    repair_attempts: int = 0,
    successful_fix: str = "",
    repair_files: Iterable[str] = (),
    repair_tests: Iterable[str] = (),
    state_before: str = "",
    state_after: str = "",
    checkpoint: str = "",
    regression_status: str = "",
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Append one deduplicatable incident observation without storing secrets."""
    now = (now_utc or datetime.now(UTC)).astimezone(UTC).isoformat()
    safe_evidence = _sanitize_mapping(evidence)
    fingerprint_seed = {
        "incident_type": incident_type,
        "component": component,
        "error_code": error_code,
        "root_cause": root_cause,
    }
    fingerprint = _content_hash(fingerprint_seed)
    previous = [
        item
        for item in _read_jsonl_tail(Path(path), limit=1000)
        if item.get("fingerprint") == fingerprint
    ]
    latest = previous[-1] if previous else {}
    effective_regression_status = regression_status or (
        "REGRESSION"
        if latest.get("successful_fix")
        else "RECURRING"
        if previous
        else "NEW"
    )
    record: dict[str, object] = {
        "schema": "odin.autonomous_demo_incident/v1",
        "fingerprint": fingerprint,
        "incident_type": incident_type,
        "component": component,
        "error_code": error_code,
        "root_cause": root_cause,
        "evidence_hash": _content_hash(safe_evidence),
        "first_seen": latest.get("first_seen", now),
        "last_seen": now,
        "occurrences": _nonnegative_int(latest.get("occurrences")) + 1,
        "repair_attempts": max(
            _nonnegative_int(latest.get("repair_attempts")),
            max(0, int(repair_attempts)),
        ),
        "successful_fix": successful_fix or str(latest.get("successful_fix", "")),
        "repair_files": _safe_string_list(repair_files)
        or _safe_string_list(latest.get("repair_files", [])),
        "repair_tests": _safe_string_list(repair_tests)
        or _safe_string_list(latest.get("repair_tests", [])),
        "state_before": _safe_scalar(state_before)
        or _safe_scalar(latest.get("state_before", "")),
        "state_after": _safe_scalar(state_after)
        or _safe_scalar(latest.get("state_after", "")),
        "checkpoint": checkpoint or str(latest.get("checkpoint", "")),
        "regression_status": effective_regression_status,
        **GLOBAL_GUARDRAILS,
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def append_repair_evidence(
    path: str | Path,
    *,
    fingerprint: str,
    successful_fix: str,
    repair_attempts: int,
    repair_files: Iterable[str],
    repair_tests: Iterable[str],
    state_before: str,
    state_after: str,
    checkpoint: str,
    regression_status: str = "RESOLVED",
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Append repair metadata without fabricating a new incident occurrence."""
    target = Path(path)
    matches = [
        item
        for item in _read_jsonl_tail(target, limit=1000)
        if item.get("fingerprint") == fingerprint
    ]
    if not matches:
        raise ValueError("autonomous_demo_incident_fingerprint_not_found")
    if not successful_fix:
        raise ValueError("autonomous_demo_successful_fix_required")
    latest = dict(matches[-1])
    now = (now_utc or datetime.now(UTC)).astimezone(UTC).isoformat()
    latest.update(
        {
            "repair_attempts": max(
                _nonnegative_int(latest.get("repair_attempts")),
                max(0, int(repair_attempts)),
            ),
            "successful_fix": _safe_scalar(successful_fix),
            "repair_files": _safe_string_list(repair_files),
            "repair_tests": _safe_string_list(repair_tests),
            "state_before": _safe_scalar(state_before),
            "state_after": _safe_scalar(state_after),
            "checkpoint": _safe_scalar(checkpoint),
            "regression_status": _safe_scalar(regression_status),
            "repair_annotation": True,
            "repair_annotated_at": now,
            **GLOBAL_GUARDRAILS,
        }
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(latest, sort_keys=True) + "\n")
    return latest


def read_control(path: str | Path) -> dict[str, object]:
    """Read an operator request. Missing or invalid input fails to PAUSE."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"action": "PAUSE", "reason": "operator_control_missing_or_invalid"}
    if not isinstance(value, dict) or value.get("action") not in ALLOWED_CONTROLS:
        return {"action": "PAUSE", "reason": "operator_control_missing_or_invalid"}
    return {
        "action": value["action"],
        "request_id": str(value.get("request_id", "")),
        "requested_at_utc": str(value.get("requested_at_utc", "")),
    }


def request_control(
    path: str | Path,
    *,
    action: str,
    request_id: str,
    resume_confirmed: bool = False,
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Persist an operator request; RESUME is only a revalidation request."""
    normalized = action.strip().upper()
    if normalized not in ALLOWED_CONTROLS:
        return _control_block("operator_control_action_invalid")
    if normalized == "RESUME" and not resume_confirmed:
        return _control_block("resume_visual_confirmation_required")
    if not request_id:
        return _control_block("operator_control_request_id_missing")
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    payload: dict[str, object] = {
        "schema": "odin.autonomous_demo_control/v1",
        "action": normalized,
        "request_id": request_id,
        "requested_at_utc": now.isoformat(),
        "resume_requires_full_gate_revalidation": normalized == "RESUME",
        **GLOBAL_GUARDRAILS,
    }
    _atomic_json(Path(path), payload)
    return {"status": "ACCEPTED", **payload}


def autonomous_demo_dashboard_state(
    *,
    state_path: str | Path,
    heartbeat_path: str | Path,
    incidents_path: str | Path,
    report_root: str | Path | None = None,
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Read a bounded operational summary for the local dashboards."""
    current = read_state(state_path)
    heartbeat = _read_json(Path(heartbeat_path))
    incidents = _deduplicate_incidents(_read_jsonl_tail(Path(incidents_path), limit=1000))[-20:]
    reports = Path(report_root) if report_root is not None else None
    metrics = _read_json(reports / "ODIN_AUTONOMOUS_DEMO_METRICS.json") if reports else {}
    hermes_vs_reality = (
        _read_jsonl_tail(reports / "ODIN_HERMES_VS_REALITY.jsonl", limit=20) if reports else []
    )
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    heartbeat_at = _parse_utc(heartbeat.get("heartbeat_at_utc"))
    heartbeat_age = int((now - heartbeat_at).total_seconds()) if heartbeat_at is not None else None
    heartbeat_fresh = heartbeat_age is not None and 0 <= heartbeat_age <= 120
    observed = current.get("observed")
    safe_observed = observed if isinstance(observed, dict) else {}
    return {
        "status": "OK" if current.get("status") != "BLOCKED" and heartbeat_fresh else "DEGRADED",
        "mode": "ODIN_AUTONOMOUS_DEMO_RC2",
        "supervisor": current,
        "heartbeat": {
            "state": heartbeat.get("state", "UNAVAILABLE"),
            "cycle": heartbeat.get("cycle"),
            "started_at_utc": heartbeat.get("started_at_utc"),
            "heartbeat_at_utc": heartbeat.get("heartbeat_at_utc"),
            "next_check_at_utc": heartbeat.get("next_check_at_utc"),
            "age_seconds": heartbeat_age,
            "fresh": heartbeat_fresh,
        },
        "incidents": incidents,
        "incident_count_visible": len(incidents),
        "metrics": metrics,
        "hermes_vs_reality": hermes_vs_reality,
        "financial": {
            key: safe_observed.get(key)
            for key in (
                "balance",
                "equity",
                "margin",
                "free_margin",
                "daily_realized_pnl",
                "completed_trades_today",
                "positions_count",
                "orders_count",
                "floating_pnl",
                "drawdown_percent",
                "daily_loss_remaining_eur",
                "max_completed_trades_per_day",
                "max_simultaneous_positions",
            )
        },
        "market": {
            key: safe_observed.get(key)
            for key in (
                "logical_symbol",
                "broker_symbol",
                "bid",
                "ask",
                "spread",
                "spread_points",
                "spread_pips",
                "spread_limit",
                "spread_limit_points",
                "data_freshness",
                "data_age_seconds",
                "normalized_event_time_utc",
                "time_profile",
                "market_open",
                "symbol_trade_mode",
            )
        },
        "decision": safe_observed.get("latest_decision"),
        "risk": safe_observed.get("risk"),
        "execution": safe_observed.get("execution"),
        **GLOBAL_GUARDRAILS,
    }


def _atomic_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_jsonl_tail(path: Path, *, limit: int) -> list[dict[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    except OSError:
        return []
    result: list[dict[str, object]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            result.append(_sanitize_mapping(value))
    return result


def _deduplicate_incidents(records: list[dict[str, object]]) -> list[dict[str, object]]:
    latest: dict[str, dict[str, object]] = {}
    order: list[str] = []
    for record in records:
        fingerprint = str(record.get("fingerprint", ""))
        if not fingerprint:
            continue
        if fingerprint not in latest:
            order.append(fingerprint)
        latest[fingerprint] = record
    return [latest[fingerprint] for fingerprint in order]


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _nonnegative_int(value: object) -> int:
    return max(0, int(value)) if isinstance(value, (int, float)) else 0


def _safe_string_list(value: object) -> list[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        return []
    return [safe for item in value if (safe := _safe_scalar(item))][:20]


def _safe_scalar(value: object) -> str:
    if not isinstance(value, (str, int, float, bool)):
        return ""
    text = str(value).strip().replace("\r", " ").replace("\n", " ")
    forbidden = ("password", "token", "secret", "credential")
    return "REDACTED" if any(part in text.casefold() for part in forbidden) else text[:500]


def _content_hash(value: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _sanitize_mapping(value: Mapping[str, object]) -> dict[str, object]:
    forbidden = ("password", "token", "secret", "credential")
    result: dict[str, object] = {}
    for key, item in value.items():
        if any(part in key.casefold() for part in forbidden):
            continue
        if isinstance(item, Mapping):
            result[str(key)] = _sanitize_mapping(item)
        elif isinstance(item, (str, int, float, bool)) or item is None:
            result[str(key)] = item
        elif isinstance(item, (list, tuple)):
            result[str(key)] = [
                _sanitize_mapping(entry) if isinstance(entry, Mapping) else entry
                for entry in item
                if isinstance(entry, (Mapping, str, int, float, bool)) or entry is None
            ]
    return result


def _blocked(reason: str) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "state": "EXECUTION_PAUSED",
        "reason": reason,
        **GLOBAL_GUARDRAILS,
    }


def _control_block(reason: str) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "reason": reason,
        **GLOBAL_GUARDRAILS,
    }

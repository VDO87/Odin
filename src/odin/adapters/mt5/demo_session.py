"""Persisted, fail-closed preparation state for a future supervised MT5 demo."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from .demo_guard import demo_account_guard


def detect_terminal_installation(terminal_path: str | None) -> dict[str, object]:
    """Detect only the presence of a configured file; never start or connect to it."""
    path = Path(terminal_path) if terminal_path else None
    detected = bool(path and path.is_file())
    return {
        "status": "OK" if detected else "BLOCKED",
        "component": "mt5_terminal_detection",
        "terminal_detected": detected,
        "terminal_path": str(path) if path else "missing",
        "terminal_connection_attempted": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
        "reason": "terminal_detected_only" if detected else "terminal_not_detected",
    }


def prepare_demo_session(
    *,
    account_mode: str | None,
    terminal_path: str | None,
    state_path: str,
    kill_switch_engaged: bool,
) -> dict[str, object]:
    """Persist one redacted preparation record without access material, terminal sign-in, or actions."""
    account = demo_account_guard(account_mode)
    terminal = detect_terminal_installation(terminal_path)
    reasons = []
    if account["status"] != "READY_FOR_REVIEW":
        reasons.append(str(account["reason"]))
    if terminal["status"] != "OK":
        reasons.append(str(terminal["reason"]))
    if kill_switch_engaged:
        reasons.append("kill_switch_engaged")
    ready = not reasons
    fingerprint = _fingerprint(account_mode, terminal_path, kill_switch_engaged)
    payload = {
        "component": "mt5_demo_session",
        "status": "READY_FOR_REVIEW" if ready else "BLOCKED",
        "fingerprint": fingerprint,
        "account_mode": "demo" if account["account_mode_accepted"] else "rejected",
        "terminal_detected": terminal["terminal_detected"],
        "kill_switch_engaged": kill_switch_engaged,
        "operator_login_authorized": False,
        "terminal_connection_attempted": False,
        "access_material_present": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
        "reason": "demo_preparation_pending_operator_review" if ready else reasons[0],
        "blocked_reasons": reasons,
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    target = Path(state_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    previous = _read_state(target)
    if previous and previous.get("fingerprint") == fingerprint:
        payload["updated_at"] = previous.get("updated_at", payload["updated_at"])
        payload["idempotent_reuse"] = True
    else:
        payload["idempotent_reuse"] = False
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return {**payload, "state_path": str(target)}


def reconcile_demo_session(state_path: str) -> dict[str, object]:
    """Read a saved preparation record and retain a blocking execution posture."""
    state = _read_state(Path(state_path))
    if not state:
        return _blocked("demo_session_state_missing")
    engaged = state.get("kill_switch_engaged") is True
    if state.get("account_mode") != "demo" or engaged:
        return _blocked("demo_session_state_not_eligible", kill_switch_engaged=engaged)
    return {
        "status": "READY_FOR_REVIEW",
        "component": "mt5_demo_reconciliation",
        "fingerprint": state.get("fingerprint", ""),
        "reconciled": True,
        "kill_switch_engaged": False,
        "terminal_connection_attempted": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
        "next_safe_action": "operator_review_before_demo_login",
    }


def _fingerprint(account_mode: str | None, terminal_path: str | None, kill_switch: bool) -> str:
    value = f"{(account_mode or '').strip().lower()}|{terminal_path or ''}|{kill_switch}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_state(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _blocked(reason: str, *, kill_switch_engaged: bool = False) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "component": "mt5_demo_reconciliation",
        "reason": reason,
        "kill_switch_engaged": kill_switch_engaged,
        "terminal_connection_attempted": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }

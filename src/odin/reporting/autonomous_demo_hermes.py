"""Bounded local Hermes analysis for factual Autonomous DEMO RC2 events.

The model is an observer only.  It receives a compact redacted fact packet,
produces structured claims, and never feeds Strategy, Risk, or Execution.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from odin.contracts.events import redact_for_audit
from odin.trading.execution_ledger import closed_execution_records


HermesRunner = Callable[[str, str], dict[str, object]]

_GUARDRAILS = {
    "safe_to_trade": False,
    "real_trading": False,
    "execution_allowed": False,
    "financial_authority": False,
}
_ALLOWED_KINDS = {
    "TRADE_CLOSED": {
        "trade_execution_status",
        "trade_reconciliation_status",
        "trade_realized_pnl",
    },
    "INCIDENT": {
        "incident_error_code",
        "incident_occurrences",
        "incident_regression_status",
        "incident_root_cause",
    },
    "NO_TRADE": {"decision_reason_codes", "decision_signal"},
    "DAILY_SUMMARY": {
        "autonomous_trade_count",
        "daily_realized_pnl",
        "runtime_state",
    },
}
_LIST_KINDS = {"decision_reason_codes"}
_WORKER_TIMEOUT_SECONDS = 55.0
_SECRET_ENV_MARKERS = ("TOKEN", "PASSWORD", "SECRET", "LOGIN", "ACCOUNT_ID", "ODIN_OANDA")


def run_next_hermes_reality_analysis(
    *,
    supervisor_state: dict[str, object],
    ledger_path: str | Path,
    incidents_path: str | Path,
    claims_path: str | Path,
    analysis_events_path: str | Path,
    audit_log_path: str | Path,
    runner: HermesRunner | None = None,
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Analyze at most one previously unseen factual trigger."""
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    events_target = Path(analysis_events_path)
    processed = {
        str(item.get("trigger_id"))
        for item in _read_jsonl(events_target)
        if item.get("trigger_id")
    }
    candidate = _next_candidate(
        supervisor_state=supervisor_state,
        closed=closed_execution_records(ledger_path),
        incidents=_latest_incidents(_read_jsonl(Path(incidents_path))),
        processed=processed,
        now=now,
    )
    if candidate is None:
        return {"status": "NO_PENDING_ANALYSIS", **_GUARDRAILS}

    context = redact_for_audit(candidate["facts"])
    context_hash = _digest(context)
    task_id = f"rc2-hermes-{_digest(candidate['trigger_id'])[:16]}"
    result = (runner or _default_runner(audit_log_path))(task_id, _prompt(candidate, context))
    model = _text(result.get("model"), default="UNAVAILABLE", limit=120)
    latency_ms = _latency_ms(result.get("duration_seconds"))
    claims: list[dict[str, object]] = []
    status = "MODEL_UNAVAILABLE"
    if result.get("status") == "success":
        claims = _parse_claims(
            result.get("response"),
            candidate=candidate,
            model=model,
            latency_ms=latency_ms,
            context_hash=context_hash,
            now=now,
        )
        status = "ANALYZED" if claims else "INVALID_MODEL_OUTPUT"
    if claims:
        _append_jsonl(Path(claims_path), claims)
    event: dict[str, object] = {
        "schema": "odin.hermes_reality_analysis/v1",
        "timestamp_utc": now.isoformat(),
        "trigger_id": candidate["trigger_id"],
        "trigger_type": candidate["trigger_type"],
        "subject_id": candidate["subject_id"],
        "status": status,
        "claims_count": len(claims),
        "model": model,
        "latency_ms": latency_ms,
        "context_hash": context_hash,
        "model_error_code": _model_error_code(result),
        **_GUARDRAILS,
    }
    _append_jsonl(events_target, [event])
    return {"status": status, "event": event, "claims": claims, **_GUARDRAILS}


def _next_candidate(
    *,
    supervisor_state: dict[str, object],
    closed: list[dict[str, object]],
    incidents: list[dict[str, object]],
    processed: set[str],
    now: datetime,
) -> dict[str, Any] | None:
    for record in closed:
        subject = _text(record.get("decision_id"), default="UNIDENTIFIED", limit=160)
        trigger = f"trade:{subject}"
        if trigger not in processed:
            return {
                "trigger_id": trigger,
                "trigger_type": "TRADE_CLOSED",
                "subject_id": subject,
                "facts": {
                    key: record.get(key)
                    for key in (
                        "decision_id",
                        "execution_status",
                        "reconciliation_status",
                        "realized_pnl",
                        "side",
                        "requested_volume",
                        "executed_volume",
                        "slippage",
                        "close_time",
                    )
                },
            }
    for record in incidents:
        subject = _text(record.get("fingerprint"), default="UNIDENTIFIED", limit=128)
        trigger = f"incident:{subject}"
        if trigger not in processed:
            return {
                "trigger_id": trigger,
                "trigger_type": "INCIDENT",
                "subject_id": subject,
                "facts": {
                    key: record.get(key)
                    for key in (
                        "fingerprint",
                        "incident_type",
                        "component",
                        "error_code",
                        "root_cause",
                        "occurrences",
                        "repair_attempts",
                        "successful_fix",
                        "regression_status",
                        "checkpoint",
                    )
                },
            }
    observed = _as_dict(supervisor_state.get("observed"))
    decision = _as_dict(observed.get("latest_decision"))
    if decision.get("signal") == "NO_TRADE":
        subject = now.date().isoformat()
        trigger = f"no-trade:{subject}"
        if trigger not in processed:
            return {
                "trigger_id": trigger,
                "trigger_type": "NO_TRADE",
                "subject_id": subject,
                "facts": {
                    "signal": decision.get("signal"),
                    "reason_codes": decision.get("reason_codes", []),
                    "strategy_id": decision.get("strategy_id"),
                    "data_quality": decision.get("data_quality"),
                    "freshness": decision.get("freshness"),
                },
            }
    subject = now.date().isoformat()
    trigger = f"daily:{subject}"
    if trigger not in processed:
        autonomous_closed = [
            item
            for item in closed
            if item.get("decision_id") != "rc1-canary-human-confirmed"
        ]
        return {
            "trigger_id": trigger,
            "trigger_type": "DAILY_SUMMARY",
            "subject_id": subject,
            "facts": {
                "runtime_state": supervisor_state.get("state"),
                "daily_realized_pnl": observed.get("daily_realized_pnl"),
                "autonomous_trade_count": len(autonomous_closed),
                "data_freshness": observed.get("data_freshness"),
                "reconciliation": observed.get("reconciliation"),
                "resource_status": _as_dict(observed.get("resources")).get("status"),
            },
        }
    return None


def _prompt(candidate: dict[str, Any], context: object) -> str:
    allowed = sorted(_ALLOWED_KINDS[str(candidate["trigger_type"])])
    return "\n".join(
        (
            "You are Hermes in ODIN read-only diagnostic mode.",
            "You have no financial authority. Never suggest or request an order, position, volume, SL, TP, or permission change.",
            "Return JSON only: {\"claims\":[{\"kind\":str,\"expected\":scalar_or_string_list,\"claim\":str,\"action\":str}]}",
            "Use only the supplied facts. Produce exactly 1 concise factual claim. Do not invent missing values.",
            "Expected must be a literal value from facts. Only decision_reason_codes may be a string list.",
            "Never use the schema words scalar or string_list as an expected value.",
            f"trigger_type={candidate['trigger_type']}",
            f"subject_id={candidate['subject_id']}",
            f"allowed_kinds={json.dumps(allowed)}",
            f"facts={json.dumps(context, sort_keys=True, separators=(',', ':'))}",
        )
    )


def _parse_claims(
    response: object,
    *,
    candidate: dict[str, Any],
    model: str,
    latency_ms: int | None,
    context_hash: str,
    now: datetime,
) -> list[dict[str, object]]:
    if not isinstance(response, str) or len(response) > 16_384:
        return []
    try:
        payload = json.loads(response)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict) or not isinstance(payload.get("claims"), list):
        return []
    allowed = _ALLOWED_KINDS[str(candidate["trigger_type"])]
    claims: list[dict[str, object]] = []
    for raw in payload["claims"][:1]:
        if not isinstance(raw, dict) or raw.get("kind") not in allowed:
            continue
        expected = _expected_value(kind=str(raw["kind"]), value=raw.get("expected"))
        if expected is None:
            continue
        kind = str(raw["kind"])
        claim_id = _digest(
            {
                "trigger_id": candidate["trigger_id"],
                "kind": kind,
                "expected": expected,
            }
        )[:24]
        claim: dict[str, object] = {
            "schema": "odin.hermes_claim/v1",
            "claim_id": claim_id,
            "trigger_id": candidate["trigger_id"],
            "trigger_type": candidate["trigger_type"],
            "subject_id": candidate["subject_id"],
            "kind": kind,
            "expected": expected,
            "claim": _text(raw.get("claim"), default=kind, limit=240),
            "action": _diagnostic_action(raw.get("action")),
            "source": "HERMES_LOCAL_OLLAMA_READ_ONLY",
            "observed_at": now.isoformat(),
            "model": model,
            "latency_ms": latency_ms,
            "context_hash": context_hash,
            **_GUARDRAILS,
        }
        claims.append(claim)
    return claims


def _default_runner(audit_log_path: str | Path) -> HermesRunner:
    def run(task_id: str, prompt: str) -> dict[str, object]:
        started = time.monotonic()
        worker = Path(__file__).with_name("autonomous_demo_hermes_worker.py")
        payload = json.dumps({"task_id": task_id, "prompt": prompt})
        try:
            completed = subprocess.run(
                [sys.executable, str(worker)],
                input=payload,
                text=True,
                capture_output=True,
                check=False,
                timeout=_WORKER_TIMEOUT_SECONDS,
                env=_worker_environment(audit_log_path),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            return _worker_failure("timeout", "worker_timeout", started)
        except OSError:
            return _worker_failure("failed", "worker_launch_failed", started)
        if completed.returncode != 0:
            return _worker_failure("failed", "worker_exit_failed", started)
        if len(completed.stdout.encode("utf-8", errors="replace")) > 65_536:
            return _worker_failure("failed", "worker_output_too_large", started)
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return _worker_failure("failed", "worker_output_invalid", started)
        if not isinstance(result, dict):
            return _worker_failure("failed", "worker_output_invalid", started)
        return result

    return run


def _worker_environment(audit_log_path: str | Path) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in _SECRET_ENV_MARKERS)
    }
    source_root = str(Path(__file__).resolve().parents[2])
    python_path = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        source_root + os.pathsep + python_path if python_path else source_root
    )
    environment["ODIN_HERMES_WORKER_AUDIT_LOG_PATH"] = str(audit_log_path)
    return environment


def _worker_failure(status: str, error: str, started: float) -> dict[str, object]:
    return {
        "status": status,
        "model": "UNAVAILABLE",
        "duration_seconds": round(time.monotonic() - started, 3),
        "error": error,
    }


def _latest_incidents(records: list[dict[str, object]]) -> list[dict[str, object]]:
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


def _append_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(redact_for_audit(record), sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    result: list[dict[str, object]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            result.append(value)
    return result


def _expected_value(
    *, kind: str, value: object
) -> bool | int | float | str | list[str] | None:
    if kind not in _LIST_KINDS and isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str) and value and len(value) <= 160:
        if value.casefold() in {"scalar", "string_list"}:
            return None
        return value
    if kind in _LIST_KINDS and (
        isinstance(value, list)
        and len(value) <= 12
        and all(isinstance(item, str) and len(item) <= 120 for item in value)
    ):
        return value
    return None


def _diagnostic_action(value: object) -> str:
    action = _text(value, default="NO_ACTION", limit=240)
    prohibited = ("order_send", "buy", "sell", "open position", "close position")
    return "NO_ACTION" if any(item in action.casefold() for item in prohibited) else action


def _model_error_code(result: dict[str, object]) -> str | None:
    if result.get("status") == "success":
        return None
    error = str(result.get("error", "model_unavailable")).casefold()
    if "timeout" in error:
        return "MODEL_TIMEOUT"
    if "cancel" in error:
        return "MODEL_CANCELLED"
    return "MODEL_UNAVAILABLE"


def _latency_ms(value: object) -> int | None:
    return round(float(value) * 1000) if isinstance(value, (int, float)) else None


def _text(value: object, *, default: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        return default
    return " ".join(value.split())[:limit]


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}

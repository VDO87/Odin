"""Manual, evidence-only supervision and weekly evolution reports for ODIN.

This module deliberately does not schedule itself, change code, or invoke a
trading API.  It turns the already available local observations into a bounded
operator handoff and records how any supplied Hermes claims compare with
observable facts.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from odin.contracts.events import redact_for_audit
from odin.dashboard.routes import DashboardRoutes


_GUARDRAILS: dict[str, bool] = {
    "safe_to_trade": False,
    "real_trading": False,
    "execution_allowed": False,
}
_CLAIM_KEYS = {
    "action",
    "claim",
    "claim_id",
    "context_hash",
    "expected",
    "kind",
    "latency_ms",
    "model",
    "observed_at",
    "source",
    "subject_id",
    "trigger_id",
    "trigger_type",
}
_RESULTS = {"CONFIRMED", "PARTIAL", "NOT_CONFIRMED", "CONTRADICTED"}
_ROOT_CAUSES = {
    "PROMPT",
    "WEAK_SOURCE",
    "STALE_SOURCE",
    "STALE_CONTEXT",
    "MISSING_CONTEXT",
    "HALLUCINATION",
    "INTEGRATION",
    "MODEL_LIMITATION",
    "UNKNOWN",
}


def write_daily_supervisor_report(
    *,
    output_dir: str,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
    claims: Iterable[dict[str, object]] = (),
    source_snapshot: dict[str, object] | None = None,
    dashboard_probe: Callable[[], dict[str, object]] | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Persist one manual Daily Supervisor report without taking an action."""
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    snapshot = source_snapshot or _collect_snapshot(log_path=log_path, sqlite_path=sqlite_path)
    dashboard = (dashboard_probe or probe_local_dashboards)()
    scorecard = score_hermes_vs_reality(claims=claims, snapshot=snapshot)
    sections = _daily_sections(snapshot=snapshot, dashboard=dashboard, scorecard=scorecard)
    priority = _daily_priority(sections)
    report: dict[str, object] = {
        "status": "OK",
        "component": "odin_daily_supervisor",
        "generated_at": timestamp.isoformat(timespec="seconds"),
        "schedule": "MANUAL_ONLY; intended_operator_window=08:00 Europe/Lisbon",
        "read_only": True,
        **_GUARDRAILS,
        "daily_sections": sections,
        "hermes_vs_reality": scorecard,
        "priority_suggestion": priority,
        "bounded_codex_handoff": _bounded_handoff(priority=priority, sections=sections),
        "automatic_change_started": False,
        "max_daily_improvements": 1,
    }
    return _write_report(output_dir=output_dir, stem="odin-daily-supervisor", report=report, timestamp=timestamp)


def write_weekly_evolution_report(
    *,
    reports_dir: str,
    output_dir: str,
    now: datetime | None = None,
) -> dict[str, object]:
    """Evaluate the preceding seven days; propose at most one non-executing initiative."""
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    since = timestamp - timedelta(days=7)
    reports = _recent_daily_reports(Path(reports_dir), since=since)
    categories = Counter(
        str(_as_dict(report.get("priority_suggestion")).get("category", "NO_CHANGE"))
        for report in reports
        if isinstance(report.get("priority_suggestion"), dict)
    )
    score_results = Counter(
        str(item.get("result", "UNKNOWN"))
        for report in reports
        for item in _score_items(report)
    )
    initiative = _weekly_initiative(categories=categories, report_count=len(reports))
    report: dict[str, object] = {
        "status": "OK" if reports else "BLOCKED",
        "component": "odin_weekly_evolution_gate",
        "generated_at": timestamp.isoformat(timespec="seconds"),
        "schedule": "MANUAL_ONLY; intended_operator_window=Saturday 08:00 Europe/Lisbon",
        "read_only": True,
        **_GUARDRAILS,
        "window_start": since.isoformat(timespec="seconds"),
        "daily_reports_considered": len(reports),
        "priority_categories": dict(sorted(categories.items())),
        "hermes_vs_reality_results": dict(sorted(score_results.items())),
        "weekly_initiative": initiative,
        "automatic_change_started": False,
        "max_weekly_evolutions": 1,
    }
    return _write_report(output_dir=output_dir, stem="odin-weekly-evolution", report=report, timestamp=timestamp)


def score_hermes_vs_reality(
    *, claims: Iterable[dict[str, object]], snapshot: dict[str, object]
) -> dict[str, object]:
    """Score a small structured claim set against exact local observations.

    Free-form LLM text is intentionally not accepted as evidence.  Unknown
    claim kinds are retained as unconfirmed rather than inferred.
    """
    items = [_score_claim(_safe_claim(claim), snapshot) for claim in claims]
    result_counts = Counter(str(item["result"]) for item in items)
    return {
        "claims_available": bool(items),
        "claims_status": "SCORED" if items else "NO_CLAIMS_AVAILABLE",
        "items": items,
        "counts": {result: result_counts.get(result, 0) for result in sorted(_RESULTS)},
        "financial_authority": False,
    }


def probe_local_dashboards() -> dict[str, object]:
    """Check local HTTP reachability only; do not start or control a server."""
    endpoints = {
        "tradedesk": "http://127.0.0.1:8765/",
        "cockpit": "http://127.0.0.1:8765/cockpit",
    }
    results: dict[str, object] = {}
    for name, url in endpoints.items():
        try:
            with urlopen(url, timeout=3) as response:  # noqa: S310 - fixed localhost URLs
                results[name] = {"url": url, "reachable": response.status == 200, "http_status": response.status}
        except (OSError, URLError):
            results[name] = {"url": url, "reachable": False, "http_status": None}
    return results


def _collect_snapshot(*, log_path: str, sqlite_path: str) -> dict[str, object]:
    routes = DashboardRoutes(log_path=log_path, sqlite_path=sqlite_path)
    paths = {
        "operations": "/operations/overview",
        "events": "/operations/events",
        "replay": "/trading/replay",
        "demo_execution": "/trading/demo-execution",
        "shadow": "/shadow/intelligence",
        "mt5": "/mt5/demo/observation",
        "mt5_audit": "/mt5/demo/audit",
        "history": "/data/history/canonical",
        "hermes": "/hermes/summary",
    }
    snapshot: dict[str, object] = {}
    for name, path in paths.items():
        _, payload = routes.serve(path)
        snapshot[name] = redact_for_audit(payload)
    return snapshot


def _daily_sections(
    *, snapshot: dict[str, object], dashboard: dict[str, object], scorecard: dict[str, object]
) -> dict[str, object]:
    mt5 = _as_dict(snapshot.get("mt5"))
    history = _as_dict(snapshot.get("history"))
    shadow = _as_dict(snapshot.get("shadow"))
    replay = _as_dict(snapshot.get("replay"))
    operations = _as_dict(snapshot.get("operations"))
    events = _as_dict(snapshot.get("events"))
    demo_execution = _as_dict(snapshot.get("demo_execution"))
    return {
        "mt5_demo_read_only": {
            "status": mt5.get("status", "UNAVAILABLE"),
            "connected": mt5.get("connected"),
            "freshness": mt5.get("freshness", mt5.get("age_seconds")),
            "source": "MT5_DEMO_READ_ONLY",
        },
        "dashboards": dashboard,
        "finance_demo_metrics": {
            "source": "MT5_DEMO_EXECUTION_LEDGER_AND_REPLAY",
            "replay_status": replay.get("status", "UNAVAILABLE"),
            "simulated_result": replay.get("result", replay.get("pnl")),
            "decision_generated": replay.get("decision_generated", False),
            "demo_execution_status": _as_dict(demo_execution.get("execution")).get("status"),
            "demo_risk_status": _as_dict(demo_execution.get("risk")).get("status"),
            "demo_account": demo_execution.get("account", {}),
            "demo_anomalies": _as_dict(demo_execution.get("execution")).get("anomalies", []),
            "canary_confirmation_required": True,
        },
        "shadow_intelligence": {
            "status": shadow.get("status", "UNAVAILABLE"),
            "latest_shadow_decision": shadow.get("decision", shadow.get("latest_decision")),
            "risk_result": shadow.get("risk_result", shadow.get("risk")),
            "data_quality": shadow.get("data_quality", history.get("status", "UNAVAILABLE")),
            "freshness": shadow.get("freshness", shadow.get("as_of")),
        },
        "hermes_validation": {
            "status": _as_dict(snapshot.get("hermes")).get("status", "UNAVAILABLE"),
            "claims_status": scorecard.get("claims_status"),
            "score_counts": scorecard.get("counts", {}),
            "financial_authority": False,
        },
        "infrastructure": {
            "operations_status": operations.get("status", "UNAVAILABLE"),
            "recent_alerts": events.get("alerts_count", 0),
            "resources": operations.get("resources", operations.get("resource_checks", {})),
        },
    }


def _daily_priority(sections: dict[str, object]) -> dict[str, object]:
    mt5 = _as_dict(sections.get("mt5_demo_read_only"))
    shadow = _as_dict(sections.get("shadow_intelligence"))
    dashboards = _as_dict(sections.get("dashboards"))
    finance = _as_dict(sections.get("finance_demo_metrics"))
    if any(value is not False for value in _GUARDRAILS.values()):
        return _priority("SECURITY_RECONCILIATION", "guardrails must remain false", "P0")
    if str(mt5.get("status")) in {"INVALID", "BLOCKED"}:
        return _priority("SECURITY_RECONCILIATION", "MT5 read-only evidence is invalid or blocked", "P0")
    if str(shadow.get("data_quality")) in {"INVALID", "BLOCKED"}:
        return _priority("DATA_QUALITY", "historical or shadow input is not accepted", "P1")
    anomalies = finance.get("demo_anomalies")
    if isinstance(anomalies, list) and anomalies:
        return _priority("SECURITY_RECONCILIATION", "DEMO execution anomalies require review", "P0")
    if dashboards and not all(_as_dict(value).get("reachable") is True for value in dashboards.values()):
        return _priority("DASHBOARD_OBSERVABILITY", "one or more local dashboards are unreachable", "P2")
    return _priority("NO_CHANGE", "no evidence-backed technical improvement is required", "NONE")


def _priority(category: str, reason: str, severity: str) -> dict[str, object]:
    return {"category": category, "reason": reason, "severity": severity, "suggestion_only": True}


def _bounded_handoff(*, priority: dict[str, object], sections: dict[str, object]) -> dict[str, object] | None:
    if priority.get("category") == "NO_CHANGE":
        return None
    return {
        "objective": f"Investigate {priority.get('category')} without changing guardrails.",
        "evidence": priority.get("reason"),
        "scope": "diagnosis and the smallest reversible repair only",
        "baseline": "ODIN SUPERVISION & EVOLUTION LOOP",
        "guardrails": dict(_GUARDRAILS),
        "tests": "run targeted tests, ruff, defined mypy scope, git diff --check",
        "definition_of_done": "evidence-backed resolution or explicit external block",
        "stop_conditions": {
            "same_command_without_new_evidence": 2,
            "similar_hypotheses": 3,
            "human_authorization_required_for": ["dependencies", "persistent_process", "credentials", "trading"],
        },
        "source_sections": sorted(sections),
    }


def _safe_claim(claim: dict[str, object]) -> dict[str, object]:
    return {key: redact_for_audit(claim[key]) for key in _CLAIM_KEYS if key in claim}


def _score_claim(claim: dict[str, object], snapshot: dict[str, object]) -> dict[str, object]:
    kind = claim.get("kind")
    expected = claim.get("expected")
    actual: object = None
    root_cause = "UNKNOWN"
    if kind == "mt5_connected":
        actual = _as_dict(snapshot.get("mt5")).get("connected")
    elif kind == "historical_data_status":
        actual = _as_dict(snapshot.get("history")).get("status")
    elif kind == "execution_allowed":
        actual = _as_dict(snapshot.get("operations")).get("execution_allowed")
    elif kind == "demo_execution_status":
        actual = _as_dict(_as_dict(snapshot.get("demo_execution")).get("execution")).get("status")
    elif kind == "demo_reconciliation_status":
        actual = _as_dict(_as_dict(snapshot.get("demo_execution")).get("execution")).get(
            "reconciliation_status"
        )
    elif kind in {
        "trade_execution_status",
        "trade_reconciliation_status",
        "trade_realized_pnl",
    }:
        trade = _subject_record(
            snapshot.get("closed_trades"),
            key="decision_id",
            subject=claim.get("subject_id"),
        )
        actual = trade.get(
            {
                "trade_execution_status": "execution_status",
                "trade_reconciliation_status": "reconciliation_status",
                "trade_realized_pnl": "realized_pnl",
            }[str(kind)]
        )
    elif kind in {
        "incident_error_code",
        "incident_occurrences",
        "incident_regression_status",
        "incident_root_cause",
    }:
        incident = _subject_record(
            snapshot.get("incidents"),
            key="fingerprint",
            subject=claim.get("subject_id"),
        )
        actual = incident.get(
            {
                "incident_error_code": "error_code",
                "incident_occurrences": "occurrences",
                "incident_regression_status": "regression_status",
                "incident_root_cause": "root_cause",
            }[str(kind)]
        )
    elif kind == "decision_signal":
        actual = _as_dict(snapshot.get("decision")).get("signal")
    elif kind == "decision_reason_codes":
        actual = _as_dict(snapshot.get("decision")).get("reason_codes")
    elif kind in {"autonomous_trade_count", "daily_realized_pnl", "runtime_state"}:
        actual = _as_dict(snapshot.get("runtime")).get(str(kind))
    else:
        return _scored(claim, actual=None, result="NOT_CONFIRMED", root_cause="MISSING_CONTEXT")
    if actual is None:
        return _scored(claim, actual=None, result="NOT_CONFIRMED", root_cause="MISSING_CONTEXT")
    if _values_equal(actual, expected):
        return _scored(claim, actual=actual, result="CONFIRMED", root_cause="UNKNOWN")
    if kind == "historical_data_status" and {str(actual), str(expected)} <= {"OK", "VALIDATED"}:
        return _scored(claim, actual=actual, result="PARTIAL", root_cause="INTEGRATION")
    if kind == "mt5_connected" and actual is False:
        root_cause = "STALE_SOURCE"
    elif isinstance(actual, list) and isinstance(expected, list) and set(actual) & set(expected):
        return _scored(claim, actual=actual, result="PARTIAL", root_cause="MISSING_CONTEXT")
    elif claim.get("source") == "HERMES_LOCAL_OLLAMA_READ_ONLY":
        root_cause = "HALLUCINATION"
    return _scored(claim, actual=actual, result="CONTRADICTED", root_cause=root_cause)


def _scored(
    claim: dict[str, object], *, actual: object, result: str, root_cause: str
) -> dict[str, object]:
    if result not in _RESULTS or root_cause not in _ROOT_CAUSES:
        raise ValueError("invalid Hermes score classification")
    return {
        "claim_id": claim.get("claim_id", "UNIDENTIFIED"),
        "claim": claim.get("claim", claim.get("expected")),
        "kind": claim.get("kind", "UNKNOWN"),
        "subject_id": claim.get("subject_id"),
        "expected": claim.get("expected"),
        "observed": actual,
        "result": result,
        "classification": result,
        "root_cause": root_cause,
        "cause": root_cause,
        "action": claim.get("action", "NO_ACTION"),
        "evidence": {
            "source": "ODIN_FACTUAL_SNAPSHOT",
            "claim_source": claim.get("source", "UNSPECIFIED"),
            "observed": actual,
        },
        "model": claim.get("model", "NOT_REPORTED"),
        "timestamp": claim.get("observed_at"),
        "latency_ms": claim.get("latency_ms"),
        "context_hash": claim.get("context_hash"),
        "trigger_id": claim.get("trigger_id"),
        "trigger_type": claim.get("trigger_type"),
    }


def _subject_record(
    records: object, *, key: str, subject: object
) -> dict[str, object]:
    if not isinstance(records, list) or not isinstance(subject, str):
        return {}
    for record in records:
        if isinstance(record, dict) and record.get(key) == subject:
            return record
    return {}


def _values_equal(actual: object, expected: object) -> bool:
    if isinstance(actual, list) and len(actual) == 1 and not isinstance(expected, list):
        actual = actual[0]
    if isinstance(expected, list) and len(expected) == 1 and not isinstance(actual, list):
        expected = expected[0]
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) <= 1e-9
    if isinstance(actual, list) and isinstance(expected, list):
        return actual == expected
    return actual == expected


def _write_report(*, output_dir: str, stem: str, report: dict[str, object], timestamp: datetime) -> dict[str, object]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    basename = f"{stem}-{timestamp.strftime('%Y%m%dT%H%M%SZ')}"
    json_path = destination / f"{basename}.json"
    markdown_path = destination / f"{basename}.md"
    sanitized = redact_for_audit(report)
    json_path.write_text(json.dumps(sanitized, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(_markdown_report(sanitized), encoding="utf-8")
    return {**sanitized, "report_path": str(json_path), "markdown_path": str(markdown_path)}


def _markdown_report(report: dict[str, object]) -> str:
    lines = [
        f"# {report['component']}",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: {report['status']}",
        "",
        "## Guardrails",
        "",
        "- safe_to_trade=false",
        "- real_trading=false",
        "- execution_allowed=false",
        "",
        "## Evidence",
        "",
        "```json",
        json.dumps(report, indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines)


def _recent_daily_reports(directory: Path, *, since: datetime) -> list[dict[str, object]]:
    reports: list[dict[str, object]] = []
    for path in sorted(directory.glob("odin-daily-supervisor-*.json")):
        value = _read_json(path)
        if value is None:
            continue
        generated = value.get("generated_at")
        try:
            generated_at = datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
        except ValueError:
            continue
        if generated_at >= since:
            reports.append(value)
    return reports


def _weekly_initiative(*, categories: Counter[str], report_count: int) -> dict[str, object]:
    if report_count == 0:
        return {"status": "NO_EVIDENCE", "initiative": None, "automatic_change_started": False}
    for category in ("SECURITY_RECONCILIATION", "DATA_QUALITY", "DASHBOARD_OBSERVABILITY"):
        if categories.get(category, 0):
            return {
                "status": "PROPOSED_FOR_HUMAN_REVIEW",
                "initiative": category,
                "evidence_count": categories[category],
                "automatic_change_started": False,
            }
    return {"status": "NO_CHANGE_REQUIRED", "initiative": None, "automatic_change_started": False}


def _score_items(report: dict[str, object]) -> list[dict[str, object]]:
    scorecard = _as_dict(report.get("hermes_vs_reality"))
    items = scorecard.get("items", [])
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}

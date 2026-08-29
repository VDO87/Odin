"""Durable, redacted operating reports for Autonomous DEMO RC2."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Iterable

from odin.contracts.events import redact_for_audit
from odin.reporting.supervision_loop import score_hermes_vs_reality
from odin.trading.demo_decision_ledger import read_demo_decision_ledger
from odin.trading.execution_ledger import (
    analyze_execution_ledger,
    closed_execution_records,
)


_GUARDRAILS = {
    "safe_to_trade": False,
    "real_trading": False,
    "execution_allowed": False,
}
_CANARY_DECISION_ID = "rc1-canary-human-confirmed"


def update_autonomous_demo_reports(
    *,
    report_root: str | Path,
    supervisor_state: dict[str, object],
    ledger_path: str | Path,
    decision_ledger_path: str | Path,
    incidents_path: str | Path,
    hermes_claims_path: str | Path | None = None,
    hermes_analysis_events_path: str | Path | None = None,
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Update the bounded RC2 evidence set; never control or contact the broker."""
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    root = Path(report_root)
    root.mkdir(parents=True, exist_ok=True)
    observed = _as_dict(supervisor_state.get("observed"))
    ledger = analyze_execution_ledger(ledger_path)
    decision_ledger = read_demo_decision_ledger(decision_ledger_path)
    closed = closed_execution_records(ledger_path)
    autonomous_closed = [
        record for record in closed if record.get("decision_id") != _CANARY_DECISION_ID
    ]
    prior = _read_json(root / "ODIN_AUTONOMOUS_DEMO_METRICS.json")
    prior_generated = _parse_utc(prior.get("generated_at_utc"))
    elapsed = max(0.0, (now - prior_generated).total_seconds()) if prior_generated else 0.0
    monitored_increment = (
        min(elapsed, 300.0)
        if observed.get("market_open") is True and observed.get("data_freshness") == "FRESH"
        else 0.0
    )
    market_open_seconds = _number(prior.get("market_open_seconds"))
    market_open_seconds += monitored_increment
    ledger_metrics = _as_dict(ledger.get("metrics"))
    current_drawdown = _number(observed.get("drawdown_percent"))
    max_drawdown = max(_number(prior.get("max_drawdown_percent")), current_drawdown)
    metrics: dict[str, object] = {
        "schema": "odin.autonomous_demo_metrics/v1",
        "generated_at_utc": now.isoformat(),
        "runtime_state": supervisor_state.get("state"),
        "branch": supervisor_state.get("branch"),
        "checkpoint": supervisor_state.get("checkpoint"),
        "market_open_seconds": round(market_open_seconds, 3),
        "market_open_hours": round(market_open_seconds / 3600, 6),
        "demo_trades_total": len(closed),
        "autonomous_demo_trades": len(autonomous_closed),
        "reconciled_trades": len(closed),
        "rejected": ledger_metrics.get("rejected", 0),
        "duplicates": 1 if "duplicate_submission" in _string_list(ledger.get("anomalies")) else 0,
        "orphan_positions": observed.get("positions_count", 0)
        if supervisor_state.get("state") == "RECONCILING"
        else 0,
        "realized_pnl": ledger.get("realized_pnl", 0.0),
        "daily_realized_pnl": observed.get("daily_realized_pnl"),
        "completed_trades_today": observed.get("completed_trades_today"),
        "win_rate_percent": ledger_metrics.get("win_rate_percent"),
        "profit_factor": ledger_metrics.get("profit_factor"),
        "expectancy": ledger_metrics.get("expectancy"),
        "average_spread": ledger_metrics.get("average_spread"),
        "average_slippage": ledger_metrics.get("average_slippage"),
        "rejection_rate_percent": ledger_metrics.get("rejection_rate_percent", 0.0),
        "reconciliation_errors": ledger_metrics.get("reconciliation_errors", 0),
        "floating_pnl": observed.get("floating_pnl"),
        "current_drawdown_percent": current_drawdown,
        "max_drawdown_percent": round(max_drawdown, 4),
        "positions_count": observed.get("positions_count", 0),
        "orders_count": observed.get("orders_count", 0),
        "decision_ledger_status": decision_ledger.get("status"),
        "execution_ledger_status": ledger.get("status"),
        **_GUARDRAILS,
    }
    _atomic_json(root / "ODIN_AUTONOMOUS_DEMO_METRICS.json", metrics)
    _write_closed_trades(root / "ODIN_AUTONOMOUS_DEMO_TRADES.jsonl", autonomous_closed)
    incidents = _read_jsonl(Path(incidents_path))
    _write_status(root / "ODIN_AUTONOMOUS_DEMO_STATUS.md", supervisor_state, metrics)
    _write_incidents(root / "ODIN_AUTONOMOUS_DEMO_INCIDENTS.md", incidents)
    _write_repairs(root / "ODIN_AUTONOMOUS_DEMO_REPAIRS.md", incidents)
    _write_acceptance(root / "ODIN_AUTONOMOUS_DEMO_ACCEPTANCE_REPORT.md", metrics)
    hermes = _update_hermes_journal(
        root / "ODIN_HERMES_VS_REALITY.jsonl",
        supervisor_state=supervisor_state,
        claims=_read_jsonl(Path(hermes_claims_path)) if hermes_claims_path else [],
        analyses=(
            _read_jsonl(Path(hermes_analysis_events_path))
            if hermes_analysis_events_path
            else []
        ),
        closed=closed,
        incidents=incidents,
        now=now,
    )
    return {
        "status": "UPDATED",
        "report_root": str(root),
        "metrics": metrics,
        "hermes_vs_reality": hermes,
        **_GUARDRAILS,
    }


def _write_status(path: Path, state: dict[str, object], metrics: dict[str, object]) -> None:
    observed = _as_dict(state.get("observed"))
    lines = [
        "# ODIN Autonomous DEMO Status",
        "",
        f"Updated UTC: {state.get('updated_at_utc', 'UNAVAILABLE')}",
        f"State: {state.get('state', 'DEGRADED')}",
        f"Branch/checkpoint: {state.get('branch', '')} / {state.get('checkpoint', '')}",
        f"Broker/server: {observed.get('broker', 'UNAVAILABLE')} / {observed.get('server', 'UNAVAILABLE')}",
        f"Symbol: {observed.get('logical_symbol', 'EURUSD')} -> {observed.get('broker_symbol', 'EURUSD.pro')}",
        f"MT5 connected: {observed.get('terminal_connected', False)}",
        f"Market freshness: {observed.get('data_freshness', 'UNAVAILABLE')}",
        f"Positions/orders: {observed.get('positions_count', 0)} / {observed.get('orders_count', 0)}",
        f"Autonomous trades reconciled: {metrics.get('autonomous_demo_trades', 0)}",
        f"Market-open soak hours: {metrics.get('market_open_hours', 0)}",
        "",
        "safe_to_trade=false",
        "real_trading=false",
        "execution_allowed=false",
    ]
    _atomic_text(path, "\n".join(lines) + "\n")


def _write_incidents(path: Path, incidents: list[dict[str, object]]) -> None:
    lines = ["# ODIN Autonomous DEMO Incidents", ""]
    if not incidents:
        lines.append("No incidents recorded.")
    for item in incidents:
        lines.append(
            f"- {item.get('last_seen', 'UNKNOWN')} | {item.get('incident_type', 'UNKNOWN')} | "
            f"{item.get('error_code', 'UNKNOWN')} | occurrences={item.get('occurrences', 1)}"
        )
    _atomic_text(path, "\n".join(lines) + "\n")


def _write_repairs(path: Path, incidents: list[dict[str, object]]) -> None:
    repairs = [item for item in incidents if item.get("successful_fix")]
    lines = ["# ODIN Autonomous DEMO Repairs", ""]
    if not repairs:
        lines.append("No autonomous code repair has been applied by the runtime.")
    for item in repairs:
        lines.append(
            f"- {item.get('last_seen', 'UNKNOWN')} | {item.get('successful_fix')} | "
            f"checkpoint={item.get('checkpoint', 'UNAVAILABLE')}"
        )
    _atomic_text(path, "\n".join(lines) + "\n")


def _write_acceptance(path: Path, metrics: dict[str, object]) -> None:
    soak_ok = _number(metrics.get("market_open_hours")) >= 24.0
    trades_ok = _integer(metrics.get("autonomous_demo_trades")) >= 5
    ledger_ok = (
        metrics.get("execution_ledger_status") == "OK"
        and metrics.get("decision_ledger_status") == "OK"
        and metrics.get("duplicates") == 0
        and metrics.get("orphan_positions") == 0
    )
    status = "ELIGIBLE_FOR_FINAL_AUDIT" if soak_ok and trades_ok and ledger_ok else "NOT_READY"
    lines = [
        "# ODIN Autonomous DEMO Operations RC2 — Acceptance",
        "",
        f"Status: {status}",
        f"- 24h market-open soak: {'PASS' if soak_ok else 'PENDING'} ({metrics.get('market_open_hours', 0)} h)",
        f"- 5 autonomous DEMO trades: {'PASS' if trades_ok else 'PENDING'} ({metrics.get('autonomous_demo_trades', 0)})",
        f"- Ledgers/duplicates/orphans: {'PASS' if ledger_ok else 'BLOCKED'}",
        "- Final suite and recovery acceptance: PENDING until the operational thresholds pass.",
        "",
        "safe_to_trade=false",
        "real_trading=false",
        "execution_allowed=false",
    ]
    _atomic_text(path, "\n".join(lines) + "\n")


def _write_closed_trades(path: Path, records: list[dict[str, object]]) -> None:
    lines = [json.dumps(redact_for_audit(record), sort_keys=True) for record in records]
    _atomic_text(path, "\n".join(lines) + ("\n" if lines else ""))


def _update_hermes_journal(
    path: Path,
    *,
    supervisor_state: dict[str, object],
    claims: Iterable[dict[str, object]],
    analyses: list[dict[str, object]],
    closed: list[dict[str, object]],
    incidents: list[dict[str, object]],
    now: datetime,
) -> dict[str, object]:
    observed = _as_dict(supervisor_state.get("observed"))
    claim_items = list(claims)
    snapshot = {
        "mt5": {"connected": observed.get("terminal_connected")},
        "operations": {"execution_allowed": False},
        "demo_execution": {
            "execution": {
                "status": _as_dict(observed.get("execution")).get(
                    "status", supervisor_state.get("state")
                ),
                "reconciliation_status": observed.get("reconciliation"),
            }
        },
        "closed_trades": closed,
        "incidents": incidents,
        "decision": _as_dict(observed.get("latest_decision")),
        "runtime": {
            "runtime_state": supervisor_state.get("state"),
            "daily_realized_pnl": observed.get("daily_realized_pnl"),
            "autonomous_trade_count": len(
                [
                    item
                    for item in closed
                    if item.get("decision_id") != _CANARY_DECISION_ID
                ]
            ),
        },
    }
    scorecard = score_hermes_vs_reality(claims=claim_items, snapshot=snapshot)
    context_hash = hashlib.sha256(
        json.dumps(
            {"snapshot": snapshot, "claims": claim_items, "analyses": analyses[-20:]},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    latest_analysis = analyses[-1] if analyses else {}
    record: dict[str, object] = {
        "schema": "odin.hermes_vs_reality/v1",
        "timestamp_utc": now.isoformat(),
        "trigger": latest_analysis.get("trigger_type", "DAILY_OR_STATE_CHANGE"),
        "analysis_status": latest_analysis.get("status", "NO_ANALYSIS_AVAILABLE"),
        "claims_status": scorecard.get("claims_status"),
        "items": scorecard.get("items", []),
        "counts": scorecard.get("counts", {}),
        "model": latest_analysis.get(
            "model", observed.get("hermes_model", "NOT_REPORTED")
        ),
        "latency_ms": latest_analysis.get(
            "latency_ms", observed.get("hermes_latency_ms")
        ),
        "context_hash": context_hash,
        "financial_authority": False,
        **_GUARDRAILS,
    }
    existing = _read_jsonl(path)
    if not any(item.get("context_hash") == context_hash for item in existing[-100:]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(redact_for_audit(record), sort_keys=True) + "\n")
        return {"status": "RECORDED", **record}
    return {"status": "ALREADY_RECORDED", **record}


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


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


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else None


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _number(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _integer(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) else 0


def _string_list(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    _atomic_text(path, json.dumps(redact_for_audit(value), indent=2, sort_keys=True) + "\n")


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)

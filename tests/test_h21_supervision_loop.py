from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from odin.reporting.supervision_loop import (
    score_hermes_vs_reality,
    write_daily_supervisor_report,
    write_weekly_evolution_report,
)


def _snapshot(*, mt5_connected: bool = True, history_status: str = "VALIDATED") -> dict[str, object]:
    return {
        "mt5": {"status": "OK", "connected": mt5_connected, "freshness": "FRESH"},
        "history": {"status": history_status},
        "shadow": {"status": "OK", "data_quality": history_status, "freshness": "FRESH"},
        "replay": {"status": "OK", "decision_generated": False},
        "demo_execution": {
            "execution": {
                "status": "NO ORDER",
                "reconciliation_status": "NOT_STARTED",
                "anomalies": [],
            },
            "risk": {"status": "BLOCK"},
            "account": {},
        },
        "operations": {"status": "OK", "execution_allowed": False},
        "events": {"alerts_count": 0},
        "hermes": {"status": "OK"},
    }


def _dashboards() -> dict[str, object]:
    return {
        "tradedesk": {"url": "http://127.0.0.1:8765/", "reachable": True, "http_status": 200},
        "cockpit": {"url": "http://127.0.0.1:8765/cockpit", "reachable": True, "http_status": 200},
    }


def test_daily_report_is_manual_guarded_and_redacts_claim_secrets(tmp_path) -> None:
    result = write_daily_supervisor_report(
        output_dir=str(tmp_path),
        source_snapshot=_snapshot(),
        dashboard_probe=_dashboards,
        claims=[{"claim_id": "g1", "kind": "mt5_connected", "expected": True, "token": "never-written"}],
        now=datetime(2026, 8, 22, tzinfo=UTC),
    )
    saved = json.loads((tmp_path / "odin-daily-supervisor-20260822T000000Z.json").read_text())
    assert result["status"] == "OK"
    assert result["safe_to_trade"] is False
    assert result["real_trading"] is False
    assert result["execution_allowed"] is False
    assert result["automatic_change_started"] is False
    assert saved["priority_suggestion"]["category"] == "NO_CHANGE"
    assert saved["hermes_vs_reality"]["items"][0]["result"] == "CONFIRMED"
    assert "never-written" not in (tmp_path / "odin-daily-supervisor-20260822T000000Z.json").read_text()
    assert (tmp_path / "odin-daily-supervisor-20260822T000000Z.md").exists()


def test_claim_score_fails_closed_when_observation_is_missing_or_contradicted() -> None:
    scores = score_hermes_vs_reality(
        claims=[
            {"claim_id": "a", "kind": "mt5_connected", "expected": True},
            {"claim_id": "b", "kind": "unknown", "expected": "anything"},
        ],
        snapshot=_snapshot(mt5_connected=False),
    )
    assert scores["items"][0]["result"] == "CONTRADICTED"
    assert scores["items"][0]["root_cause"] == "STALE_SOURCE"
    assert scores["items"][1]["result"] == "NOT_CONFIRMED"
    assert scores["items"][1]["root_cause"] == "MISSING_CONTEXT"


def test_hermes_demo_execution_claims_are_scored_against_read_only_reality() -> None:
    scores = score_hermes_vs_reality(
        claims=[
            {"claim_id": "execution", "kind": "demo_execution_status", "expected": "NO ORDER"},
            {
                "claim_id": "reconciliation",
                "kind": "demo_reconciliation_status",
                "expected": "RECONCILED",
            },
        ],
        snapshot=_snapshot(),
    )

    assert scores["items"][0]["result"] == "CONFIRMED"
    assert scores["items"][1]["result"] == "CONTRADICTED"


def test_hermes_trade_and_incident_claims_retain_auditable_context() -> None:
    scores = score_hermes_vs_reality(
        claims=[
            {
                "claim_id": "trade-pnl",
                "kind": "trade_realized_pnl",
                "subject_id": "decision-1",
                "expected": -0.88,
                "claim": "Trade realized minus 0.88 EUR.",
                "action": "Review the deterministic exit.",
                "source": "HERMES_LOCAL_OLLAMA_READ_ONLY",
                "model": "local-model",
                "observed_at": "2026-08-29T15:00:00Z",
                "latency_ms": 125,
                "context_hash": "context-1",
                "trigger_id": "trade:decision-1",
                "trigger_type": "TRADE_CLOSED",
            },
            {
                "claim_id": "incident-status",
                "kind": "incident_regression_status",
                "subject_id": "fingerprint-1",
                "expected": "NEW",
                "source": "HERMES_LOCAL_OLLAMA_READ_ONLY",
            },
            {
                "claim_id": "incident-error",
                "kind": "incident_error_code",
                "subject_id": "fingerprint-1",
                "expected": ["resource_probe_unavailable"],
                "source": "HERMES_LOCAL_OLLAMA_READ_ONLY",
            },
        ],
        snapshot={
            "closed_trades": [
                {
                    "decision_id": "decision-1",
                    "realized_pnl": -0.88,
                    "execution_status": "CLOSED",
                    "reconciliation_status": "RECONCILED",
                }
            ],
            "incidents": [
                {
                    "fingerprint": "fingerprint-1",
                    "error_code": "resource_probe_unavailable",
                    "regression_status": "RESOLVED",
                }
            ],
        },
    )

    confirmed, contradicted, normalized = scores["items"]
    assert confirmed["classification"] == "CONFIRMED"
    assert confirmed["evidence"]["observed"] == -0.88
    assert confirmed["action"] == "Review the deterministic exit."
    assert confirmed["model"] == "local-model"
    assert confirmed["latency_ms"] == 125
    assert confirmed["context_hash"] == "context-1"
    assert contradicted["classification"] == "CONTRADICTED"
    assert contradicted["cause"] == "HALLUCINATION"
    assert normalized["classification"] == "CONFIRMED"


def test_weekly_gate_proposes_at_most_one_human_reviewed_initiative(tmp_path) -> None:
    now = datetime(2026, 8, 22, tzinfo=UTC)
    daily = {
        "generated_at": (now - timedelta(days=1)).isoformat(),
        "priority_suggestion": {"category": "DATA_QUALITY"},
        "hermes_vs_reality": {"items": [{"result": "NOT_CONFIRMED"}]},
    }
    (tmp_path / "odin-daily-supervisor-20260821T000000Z.json").write_text(json.dumps(daily))
    result = write_weekly_evolution_report(reports_dir=str(tmp_path), output_dir=str(tmp_path), now=now)
    assert result["status"] == "OK"
    assert result["weekly_initiative"]["initiative"] == "DATA_QUALITY"
    assert result["weekly_initiative"]["automatic_change_started"] is False
    assert result["max_weekly_evolutions"] == 1
    assert result["execution_allowed"] is False


def test_weekly_gate_blocks_without_daily_evidence(tmp_path) -> None:
    result = write_weekly_evolution_report(
        reports_dir=str(tmp_path), output_dir=str(tmp_path), now=datetime(2026, 8, 22, tzinfo=UTC)
    )
    assert result["status"] == "BLOCKED"
    assert result["weekly_initiative"]["initiative"] is None
    assert result["execution_allowed"] is False

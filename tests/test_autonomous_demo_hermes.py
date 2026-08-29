from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import odin.reporting.autonomous_demo_hermes as hermes
from odin.trading.autonomous_demo_state import build_supervisor_state


NOW = datetime(2026, 8, 29, 15, tzinfo=UTC)


def _state(**observed_changes: object) -> dict[str, object]:
    observed: dict[str, object] = {
        "data_freshness": "STALE",
        "daily_realized_pnl": -0.88,
        "reconciliation": "RECONCILED",
        "resources": {"status": "WARNING"},
    }
    observed.update(observed_changes)
    return build_supervisor_state(
        "WAITING_MARKET",
        cycle=4,
        observed=observed,
        now_utc=NOW,
    )


def _closed_trade() -> dict[str, object]:
    return {
        "decision_id": "rc1-canary-human-confirmed",
        "execution_status": "CLOSED",
        "reconciliation_status": "RECONCILED",
        "realized_pnl": -0.88,
        "side": "BUY",
        "requested_volume": 0.01,
        "executed_volume": 0.01,
        "slippage": 0.00002,
        "close_time": "2026-08-28T14:01:42Z",
    }


def _write_incident(path: Path) -> None:
    records = [
        {
            "fingerprint": "incident-a",
            "incident_type": "RESOURCE_GUARD_BLOCK",
            "component": "resources",
            "error_code": "resource_probe_unavailable",
            "root_cause": "resource_guardrail_triggered",
            "occurrences": 1,
            "regression_status": "NEW",
        },
        {
            "fingerprint": "incident-a",
            "incident_type": "RESOURCE_GUARD_BLOCK",
            "component": "resources",
            "error_code": "resource_probe_unavailable",
            "root_cause": "resource_guardrail_triggered",
            "occurrences": 2,
            "successful_fix": "bounded_fix",
            "regression_status": "RESOLVED",
        },
    ]
    path.write_text(
        "".join(json.dumps(item) + "\n" for item in records),
        encoding="utf-8",
    )


def test_one_structured_analysis_per_trade_incident_and_daily_summary(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(hermes, "closed_execution_records", lambda _path: [_closed_trade()])
    incidents = tmp_path / "incidents.jsonl"
    _write_incident(incidents)
    prompts: list[str] = []

    def runner(_task_id: str, prompt: str) -> dict[str, object]:
        prompts.append(prompt)
        if "trigger_type=TRADE_CLOSED" in prompt:
            payload = {
                "claims": [
                    {
                        "kind": "trade_realized_pnl",
                        "expected": -0.88,
                        "claim": "The reconciled trade realized a loss.",
                        "action": "Do not call order_send.",
                    }
                ]
            }
        elif "trigger_type=INCIDENT" in prompt:
            payload = {
                "claims": [
                    {
                        "kind": "incident_regression_status",
                        "expected": ["RESOLVED"],
                        "claim": "The incident is resolved.",
                        "action": "Monitor recurrence.",
                    }
                ]
            }
        else:
            payload = {
                "claims": [
                    {
                        "kind": "runtime_state",
                        "expected": "WAITING_MARKET",
                        "claim": "The runtime is waiting for market data.",
                        "action": "NO_ACTION",
                    }
                ]
            }
        return {
            "status": "success",
            "model": "local-test-model",
            "duration_seconds": 0.125,
            "response": json.dumps(payload),
            "error": None,
        }

    kwargs = {
        "supervisor_state": _state(),
        "ledger_path": tmp_path / "ledger.jsonl",
        "incidents_path": incidents,
        "claims_path": tmp_path / "claims.jsonl",
        "analysis_events_path": tmp_path / "analysis.jsonl",
        "audit_log_path": tmp_path / "audit.jsonl",
        "runner": runner,
        "now_utc": NOW,
    }
    results = [hermes.run_next_hermes_reality_analysis(**kwargs) for _ in range(4)]

    assert [item["status"] for item in results] == [
        "ANALYZED",
        "ANALYZED",
        "ANALYZED",
        "NO_PENDING_ANALYSIS",
    ]
    assert len(prompts) == 3
    assert all("Produce exactly 1 concise factual claim" in prompt for prompt in prompts)
    events = [json.loads(line) for line in (tmp_path / "analysis.jsonl").read_text().splitlines()]
    assert [item["trigger_type"] for item in events] == [
        "TRADE_CLOSED",
        "INCIDENT",
        "DAILY_SUMMARY",
    ]
    claims = [json.loads(line) for line in (tmp_path / "claims.jsonl").read_text().splitlines()]
    assert len(claims) == 3
    assert claims[0]["action"] == "NO_ACTION"
    assert claims[0]["model"] == "local-test-model"
    assert claims[0]["latency_ms"] == 125
    assert claims[1]["expected"] == "RESOLVED"
    assert claims[0]["financial_authority"] is False
    assert all(item["execution_allowed"] is False for item in events + claims)


def test_unavailable_model_is_recorded_once_and_does_not_block_next_trigger(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(hermes, "closed_execution_records", lambda _path: [_closed_trade()])

    def unavailable(_task_id: str, _prompt: str) -> dict[str, object]:
        return {
            "status": "timeout",
            "model": "local-test-model",
            "duration_seconds": 45.0,
            "error": "request_timeout",
        }

    kwargs = {
        "supervisor_state": _state(),
        "ledger_path": tmp_path / "ledger.jsonl",
        "incidents_path": tmp_path / "incidents.jsonl",
        "claims_path": tmp_path / "claims.jsonl",
        "analysis_events_path": tmp_path / "analysis.jsonl",
        "audit_log_path": tmp_path / "audit.jsonl",
        "runner": unavailable,
        "now_utc": NOW,
    }
    first = hermes.run_next_hermes_reality_analysis(**kwargs)
    second = hermes.run_next_hermes_reality_analysis(**kwargs)

    assert first["status"] == "MODEL_UNAVAILABLE"
    assert first["event"]["trigger_type"] == "TRADE_CLOSED"
    assert first["event"]["model_error_code"] == "MODEL_TIMEOUT"
    assert second["event"]["trigger_type"] == "DAILY_SUMMARY"
    assert not (tmp_path / "claims.jsonl").exists()
    assert first["execution_allowed"] is False


def test_no_trade_is_limited_to_one_relevant_analysis_per_utc_day(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(hermes, "closed_execution_records", lambda _path: [])
    state = _state(
        latest_decision={
            "signal": "NO_TRADE",
            "reason_codes": ["market_closed_or_stale"],
            "strategy_id": "deterministic-demo-v1",
        }
    )

    def runner(_task_id: str, prompt: str) -> dict[str, object]:
        kind = "decision_signal" if "trigger_type=NO_TRADE" in prompt else "runtime_state"
        expected = "NO_TRADE" if kind == "decision_signal" else "WAITING_MARKET"
        return {
            "status": "success",
            "model": "local-test-model",
            "duration_seconds": 0.1,
            "response": json.dumps(
                {"claims": [{"kind": kind, "expected": expected, "claim": kind}]}
            ),
        }

    kwargs = {
        "supervisor_state": state,
        "ledger_path": tmp_path / "ledger.jsonl",
        "incidents_path": tmp_path / "incidents.jsonl",
        "claims_path": tmp_path / "claims.jsonl",
        "analysis_events_path": tmp_path / "analysis.jsonl",
        "audit_log_path": tmp_path / "audit.jsonl",
        "runner": runner,
        "now_utc": NOW,
    }
    first = hermes.run_next_hermes_reality_analysis(**kwargs)
    second = hermes.run_next_hermes_reality_analysis(**kwargs)
    third = hermes.run_next_hermes_reality_analysis(**kwargs)

    assert first["event"]["trigger_id"] == "no-trade:2026-08-29"
    assert second["event"]["trigger_id"] == "daily:2026-08-29"
    assert third["status"] == "NO_PENDING_ANALYSIS"

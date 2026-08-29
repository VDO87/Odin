from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest

from odin.reporting import autonomous_demo_reports as reports_module
from odin.reporting.autonomous_demo_reports import update_autonomous_demo_reports
from odin.trading.autonomous_demo_state import append_incident, build_supervisor_state


NOW = datetime(2026, 8, 31, 8, tzinfo=UTC)


def test_report_write_retries_transient_windows_replace_contention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "status.md"
    path.write_text("initial", encoding="utf-8")
    original_replace = Path.replace
    attempts = 0
    delays: list[float] = []

    def replace_after_contention(source: Path, target: Path) -> Path:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError(5, "simulated Windows sharing contention")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", replace_after_contention)
    monkeypatch.setattr(reports_module.time, "sleep", delays.append)

    reports_module._atomic_text(path, "updated")

    assert attempts == 2
    assert delays == [0.05]
    assert path.read_text(encoding="utf-8") == "updated"


def test_report_write_fails_closed_after_bounded_replace_contention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "status.md"
    path.write_text("initial", encoding="utf-8")
    attempts = 0
    delays: list[float] = []

    def replace_blocked(_source: Path, _target: Path) -> Path:
        nonlocal attempts
        attempts += 1
        raise PermissionError(5, "simulated persistent Windows sharing contention")

    monkeypatch.setattr(Path, "replace", replace_blocked)
    monkeypatch.setattr(reports_module.time, "sleep", delays.append)

    with pytest.raises(PermissionError):
        reports_module._atomic_text(path, "updated")

    assert attempts == 4
    assert delays == pytest.approx([0.05, 0.1, 0.15])
    assert path.read_text(encoding="utf-8") == "initial"


def _state() -> dict[str, object]:
    return build_supervisor_state(
        "NO_TRADE",
        cycle=10,
        branch="feature/autonomous-demo-operations-rc2",
        checkpoint="abc1234",
        now_utc=NOW,
        observed={
            "broker": "OANDA TMS Brokers S.A.",
            "server": "OANDATMS-MT5",
            "terminal_connected": True,
            "logical_symbol": "EURUSD",
            "broker_symbol": "EURUSD.pro",
            "market_open": True,
            "data_freshness": "FRESH",
            "positions_count": 0,
            "orders_count": 0,
            "balance": 50_000.0,
            "equity": 49_998.75,
            "daily_realized_pnl": 0.0,
            "completed_trades_today": 0,
            "floating_pnl": -1.25,
            "drawdown_percent": 0.05,
            "reconciliation": "RECONCILED",
        },
    )


def test_reports_accumulate_only_fresh_market_open_soak_and_stay_not_ready(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime"
    reports = tmp_path / "reports"
    runtime.mkdir()
    claims = runtime / "hermes_claims.jsonl"
    claims.write_text(
        json.dumps(
            {
                "claim_id": "connected",
                "kind": "mt5_connected",
                "expected": True,
                "source": "Hermes",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    append_incident(
        runtime / "incidents.jsonl",
        incident_type="DASHBOARD_RECOVERY",
        component="tradedesk_cockpit",
        error_code="dashboard_healthcheck_failed",
        root_cause="dashboard_process_unavailable",
        evidence={"health_status": "unavailable"},
        repair_attempts=1,
        successful_fix="dashboard_restarted_by_bounded_launcher",
        repair_files=["scripts/windows/Start-ODIN-Dashboard-Persistent.ps1"],
        repair_tests=["GET /health = 200"],
        state_before="DASHBOARD_UNAVAILABLE",
        state_after="DASHBOARD_RUNNING",
        checkpoint="abc1234",
        regression_status="RESOLVED",
        now_utc=NOW,
    )
    append_incident(
        runtime / "incidents.jsonl",
        incident_type="DASHBOARD_RECOVERY",
        component="tradedesk_cockpit",
        error_code="dashboard_healthcheck_failed",
        root_cause="dashboard_process_unavailable",
        evidence={"health_status": "unavailable"},
        now_utc=NOW + timedelta(seconds=1),
    )
    kwargs = {
        "report_root": reports,
        "supervisor_state": _state(),
        "ledger_path": runtime / "execution.jsonl",
        "decision_ledger_path": runtime / "decision.jsonl",
        "incidents_path": runtime / "incidents.jsonl",
        "hermes_claims_path": claims,
    }

    first = update_autonomous_demo_reports(**kwargs, now_utc=NOW)
    second = update_autonomous_demo_reports(**kwargs, now_utc=NOW + timedelta(seconds=60))
    third = update_autonomous_demo_reports(**kwargs, now_utc=NOW + timedelta(minutes=5))

    assert first["status"] == "UPDATED"
    assert second["metrics"]["market_open_seconds"] == 60.0
    assert third["metrics"]["market_open_seconds"] == 300.0
    assert len(third["metrics"]["equity_series"]) == 2
    assert third["metrics"]["equity_series"][-1]["balance"] == 50_000.0
    assert third["metrics"]["equity_series"][-1]["equity"] == 49_998.75
    assert third["metrics"]["equity_series"][-1]["floating_pnl"] == -1.25
    assert second["metrics"]["autonomous_demo_trades"] == 0
    assert second["metrics"]["floating_pnl"] == -1.25
    assert second["metrics"]["current_drawdown_percent"] == 0.05
    assert second["metrics"]["max_drawdown_percent"] == 0.05
    assert second["metrics"]["rejection_rate_percent"] == 0.0
    assert second["safe_to_trade"] is False
    acceptance = (reports / "ODIN_AUTONOMOUS_DEMO_ACCEPTANCE_REPORT.md").read_text()
    assert "Status: NOT_READY" in acceptance
    assert "24h market-open soak: PENDING" in acceptance
    assert "Initial canary fully reconciled: BLOCKED" in acceptance
    assert "Auto-start after an actual Windows reboot: FINAL_AUDIT_REQUIRED" in acceptance
    assert "Restart/recovery validated: PARTIAL" in acceptance
    assert "Full final suite: PENDING" in acceptance
    assert "may only reach ELIGIBLE_FOR_FINAL_AUDIT automatically" in acceptance
    assert (reports / "ODIN_AUTONOMOUS_DEMO_STATUS.md").exists()
    assert (reports / "ODIN_AUTONOMOUS_DEMO_TRADES.jsonl").exists()
    assert (reports / "ODIN_AUTONOMOUS_DEMO_INCIDENTS.md").exists()
    repairs = (reports / "ODIN_AUTONOMOUS_DEMO_REPAIRS.md").read_text()
    assert "dashboard_restarted_by_bounded_launcher" in repairs
    assert "Evidence hash:" in repairs
    assert "Repair attempts: 1" in repairs
    assert "Start-ODIN-Dashboard-Persistent.ps1" in repairs
    assert "GET /health = 200" in repairs
    assert "State before: DASHBOARD_UNAVAILABLE" in repairs
    assert "State after: DASHBOARD_RUNNING" in repairs
    assert "Checkpoint: abc1234" in repairs
    assert repairs.count("dashboard_restarted_by_bounded_launcher") == 1


def test_operational_thresholds_only_make_report_eligible_for_final_audit(
    tmp_path: Path,
) -> None:
    report = tmp_path / "ODIN_AUTONOMOUS_DEMO_ACCEPTANCE_REPORT.md"
    (tmp_path / "ODIN_RUNTIME_RATIONALIZATION_REPORT.md").write_text(
        "validated",
        encoding="utf-8",
    )
    state = _state()
    observed = state["observed"]
    assert isinstance(observed, dict)
    observed.update(
        {
            "account_mode": "DEMO",
            "time_profile": "oanda_tms_mt5_cet_cest_v1",
            "dashboard": "RUNNING",
            "resources": {"snapshot": {"supervisor_logical_instances": 1}},
        }
    )
    reports_module._write_acceptance(
        report,
        {
            "market_open_hours": 24.0,
            "autonomous_demo_trades": 5,
            "demo_trades_total": 6,
            "reconciled_trades": 6,
            "execution_ledger_status": "OK",
            "decision_ledger_status": "OK",
            "duplicates": 0,
            "orphan_positions": 0,
            "real_trading": False,
        },
        supervisor_state=state,
        incidents=[
            {"incident_type": "DASHBOARD_RECOVERY", "successful_fix": "fixed"},
            {"incident_type": "SCHEDULER_ORPHAN_PROCESS", "successful_fix": "fixed"},
        ],
        hermes={"status": "RECORDED"},
    )

    acceptance = report.read_text(encoding="utf-8")
    assert "Status: ELIGIBLE_FOR_FINAL_AUDIT" in acceptance
    assert "Status: PASSED" not in acceptance
    assert "Auto-start after an actual Windows reboot: FINAL_AUDIT_REQUIRED" in acceptance
    assert "Final acceptance declaration: PENDING" in acceptance


def test_hermes_claim_is_scored_once_per_unchanged_context(tmp_path: Path) -> None:
    claims = tmp_path / "claims.jsonl"
    claims.write_text(
        json.dumps(
            {
                "claim_id": "connected",
                "kind": "mt5_connected",
                "expected": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    kwargs = {
        "report_root": tmp_path / "reports",
        "supervisor_state": _state(),
        "ledger_path": tmp_path / "execution.jsonl",
        "decision_ledger_path": tmp_path / "decision.jsonl",
        "incidents_path": tmp_path / "incidents.jsonl",
        "hermes_claims_path": claims,
    }

    first = update_autonomous_demo_reports(**kwargs, now_utc=NOW)
    second = update_autonomous_demo_reports(**kwargs, now_utc=NOW + timedelta(minutes=1))

    assert first["hermes_vs_reality"]["status"] == "RECORDED"
    assert first["hermes_vs_reality"]["items"][0]["result"] == "CONFIRMED"
    assert second["hermes_vs_reality"]["status"] == "ALREADY_RECORDED"
    journal = (tmp_path / "reports/ODIN_HERMES_VS_REALITY.jsonl").read_text().splitlines()
    assert len(journal) == 1


def test_hermes_claim_arriving_after_empty_scorecard_creates_new_context(
    tmp_path: Path,
) -> None:
    claims = tmp_path / "claims.jsonl"
    kwargs = {
        "report_root": tmp_path / "reports",
        "supervisor_state": _state(),
        "ledger_path": tmp_path / "execution.jsonl",
        "decision_ledger_path": tmp_path / "decision.jsonl",
        "incidents_path": tmp_path / "incidents.jsonl",
        "hermes_claims_path": claims,
    }

    first = update_autonomous_demo_reports(**kwargs, now_utc=NOW)
    claims.write_text(
        json.dumps(
            {
                "claim_id": "connected-after-start",
                "kind": "mt5_connected",
                "expected": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    second = update_autonomous_demo_reports(**kwargs, now_utc=NOW + timedelta(seconds=1))

    assert first["hermes_vs_reality"]["claims_status"] == "NO_CLAIMS_AVAILABLE"
    assert second["hermes_vs_reality"]["claims_status"] == "SCORED"
    journal = (tmp_path / "reports/ODIN_HERMES_VS_REALITY.jsonl").read_text().splitlines()
    assert len(journal) == 2

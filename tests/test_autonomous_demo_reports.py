from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

from odin.reporting.autonomous_demo_reports import update_autonomous_demo_reports
from odin.trading.autonomous_demo_state import build_supervisor_state


NOW = datetime(2026, 8, 31, 8, tzinfo=UTC)


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
            "daily_realized_pnl": 0.0,
            "completed_trades_today": 0,
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

    assert first["status"] == "UPDATED"
    assert second["metrics"]["market_open_seconds"] == 60.0
    assert second["metrics"]["autonomous_demo_trades"] == 0
    assert second["safe_to_trade"] is False
    acceptance = (reports / "ODIN_AUTONOMOUS_DEMO_ACCEPTANCE_REPORT.md").read_text()
    assert "Status: NOT_READY" in acceptance
    assert "24h market-open soak: PENDING" in acceptance
    assert (reports / "ODIN_AUTONOMOUS_DEMO_STATUS.md").exists()
    assert (reports / "ODIN_AUTONOMOUS_DEMO_TRADES.jsonl").exists()
    assert (reports / "ODIN_AUTONOMOUS_DEMO_INCIDENTS.md").exists()
    assert (reports / "ODIN_AUTONOMOUS_DEMO_REPAIRS.md").exists()


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

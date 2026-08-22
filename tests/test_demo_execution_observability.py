from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json

from odin.dashboard.routes import DashboardRoutes
from odin.trading.demo_execution_dashboard import demo_execution_dashboard_state
from odin.trading.execution_ledger import analyze_execution_ledger


def _write_mt5_state(path, *, positions: list[dict[str, object]] | None = None) -> None:
    state: dict[str, object] = {
        "status": "CONNECTED_DEMO_READ_ONLY",
        "as_of": datetime.now(UTC).isoformat(),
        "account": {
            "currency": "EUR",
            "balance": 10_000.0,
            "equity": 9_995.0,
            "margin": 25.0,
            "free_margin": 9_970.0,
        },
        "positions": positions or [],
        "market": {
            "symbol": "EURUSD",
            "status": "OK",
            "bid": 1.1,
            "ask": 1.1001,
            "as_of": datetime.now(UTC).isoformat(),
            "candles": [],
        },
    }
    canonical = json.dumps(state, sort_keys=True, separators=(",", ":"))
    state["content_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
    path.write_text(json.dumps(state), encoding="utf-8")


def test_demo_dashboard_exposes_finance_and_permanent_blocks(tmp_path) -> None:
    mt5_state = tmp_path / "mt5.json"
    _write_mt5_state(mt5_state)

    result = demo_execution_dashboard_state(
        ledger_path=tmp_path / "ledger.jsonl",
        mt5_state_path=str(mt5_state),
    )

    assert result["status"] == "OK"
    assert result["banner"] == "DEMO MONEY — NO REAL CAPITAL"
    assert result["real_trading_banner"] == "REAL TRADING BLOCKED"
    assert result["account"] == {
        "currency": "EUR",
        "balance": 10_000.0,
        "equity": 9_995.0,
        "margin": 25.0,
        "free_margin": 9_970.0,
        "floating_pnl": 0,
        "realized_pnl": 0.0,
        "daily_pnl": 0.0,
        "drawdown_percent": 0.05,
    }
    assert result["execution"] == {
        "status": "NO ORDER",
        "reconciliation_status": "NOT_STARTED",
        "anomalies": [],
        "records_count": 0,
    }
    assert result["canary_confirmation_required"] is True
    assert result["execution_allowed"] is False
    assert result["safe_to_trade"] is False
    assert result["real_trading"] is False


def test_unexpected_broker_position_is_reconciliation_block(tmp_path) -> None:
    mt5_state = tmp_path / "mt5.json"
    _write_mt5_state(
        mt5_state,
        positions=[{"ticket": 7, "symbol": "EURUSD", "volume": 0.01, "profit": -1.0}],
    )

    result = demo_execution_dashboard_state(
        ledger_path=tmp_path / "ledger.jsonl",
        mt5_state_path=str(mt5_state),
    )

    assert result["status"] == "BLOCKED"
    assert result["execution"]["status"] == "RECONCILIATION_BLOCK"
    assert result["execution"]["anomalies"] == ["orphan_broker_position"]


def test_tampered_execution_ledger_is_visible_as_anomaly(tmp_path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"sequence": 1, "record_hash": "wrong"}\n', encoding="utf-8")

    result = analyze_execution_ledger(ledger)

    assert result["status"] == "DEGRADED"
    assert result["anomalies"] == ["ledger_integrity_mismatch"]
    assert result["execution_allowed"] is False


def test_supervision_analyzes_stale_execution_and_margin_anomaly(tmp_path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    record = {
        "sequence": 1,
        "previous_record_hash": "GENESIS",
        "proposal_id": "p1",
        "execution_status": "FILLED",
        "risk_result": {"status": "ALLOW_DEMO", "risk_approved": True},
        "freshness": "STALE",
        "stop_loss": 1.09,
        "take_profit": 1.11,
        "requested_volume": 0.01,
        "order_check_result": {"margin": -1.0},
    }
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
    record["record_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
    ledger.write_text(json.dumps(record) + "\n", encoding="utf-8")

    result = analyze_execution_ledger(ledger)

    assert result["status"] == "DEGRADED"
    assert "execution_with_stale_data" in result["anomalies"]
    assert "margin_anomaly" in result["anomalies"]


def test_dashboard_route_is_read_only_and_paths_are_injectable(tmp_path) -> None:
    mt5_state = tmp_path / "mt5.json"
    _write_mt5_state(mt5_state)
    routes = DashboardRoutes(
        log_path=str(tmp_path / "events.jsonl"),
        sqlite_path=str(tmp_path / "odin.sqlite"),
        demo_execution_ledger_path=str(tmp_path / "ledger.jsonl"),
        mt5_demo_state_path=str(mt5_state),
    )

    status, payload = routes.serve("/trading/demo-execution")

    assert status == 200
    assert payload["status"] == "OK"
    assert payload["execution_allowed"] is False


def test_tradedesk_and_cockpit_show_demo_execution_without_broker_controls() -> None:
    routes = DashboardRoutes()
    tradedesk = routes.tradedesk_html()
    cockpit = routes.cockpit_html()

    assert "DEMO MONEY — NO REAL CAPITAL" in tradedesk
    assert "REAL TRADING BLOCKED" in tradedesk
    assert "Balance · DEMO" in tradedesk
    assert "Floating P/L" in tradedesk
    assert "CANARY confirmação humana" in tradedesk
    assert "/trading/demo-execution" in tradedesk
    assert "DEMO EXECUTION RC1" in cockpit
    assert "/trading/demo-execution" in cockpit
    for page in (tradedesk, cockpit):
        assert "order_send" not in page

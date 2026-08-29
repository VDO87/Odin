"""Read-only financial summary for TradeDesk, cockpit and supervisor."""

from __future__ import annotations

from pathlib import Path

from odin.adapters.mt5.demo_readonly_state import read_demo_readonly_state
from odin.trading.execution_ledger import (
    analyze_execution_ledger,
    completed_reconciled_lifecycle,
    recent_execution_records,
)


def demo_execution_dashboard_state(
    *,
    ledger_path: str | Path = "/mnt/d/ODIN_LOCAL/runtime/demo_execution_ledger.jsonl",
    mt5_state_path: str = "/mnt/d/ODIN_LOCAL/runtime/mt5_demo_readonly.json",
) -> dict[str, object]:
    mt5 = read_demo_readonly_state(mt5_state_path)
    ledger = analyze_execution_ledger(ledger_path)
    account = _as_dict(mt5.get("account"))
    positions = mt5.get("positions")
    safe_positions = (
        [item for item in positions if isinstance(item, dict)]
        if isinstance(positions, list)
        else []
    )
    latest = _as_dict(ledger.get("latest"))
    ledger_anomalies = ledger.get("anomalies")
    anomalies = list(ledger_anomalies) if isinstance(ledger_anomalies, list) else []
    if safe_positions and latest.get("execution_status") not in {
        "FILLED",
        "SUBMITTED",
        "RECONCILED",
    }:
        anomalies.append("orphan_broker_position")
    floating_pnl = sum(
        float(position.get("profit", 0.0))
        for position in safe_positions
        if isinstance(position.get("profit", 0.0), (int, float))
    )
    execution_status = str(latest.get("execution_status", "NO ORDER"))
    if anomalies:
        execution_status = "RECONCILIATION_BLOCK"
    risk = _as_dict(latest.get("risk_result"))
    initial_canary_complete = completed_reconciled_lifecycle(
        ledger_path, "rc1-canary-human-confirmed"
    )
    timeline = _execution_timeline(recent_execution_records(ledger_path, limit=20))
    return {
        "status": "OK"
        if mt5.get("status") == "CONNECTED_DEMO_READ_ONLY" and not anomalies
        else "BLOCKED",
        "component": "demo_execution_dashboard",
        "mode": "ODIN_AUTONOMOUS_DEMO_RC2",
        "banner": "DEMO MONEY — NO REAL CAPITAL",
        "real_trading_banner": "REAL TRADING BLOCKED",
        "mt5_status": mt5.get("status", "BLOCKED"),
        "account": {
            "currency": account.get("currency"),
            "balance": account.get("balance"),
            "equity": account.get("equity"),
            "margin": account.get("margin"),
            "free_margin": account.get("free_margin"),
            "floating_pnl": round(floating_pnl, 2),
            "realized_pnl": ledger.get("realized_pnl", 0.0),
            "daily_pnl": ledger.get("realized_pnl", 0.0),
            "drawdown_percent": _drawdown(account),
        },
        "decision": {
            "decision_id": latest.get("decision_id"),
            "proposal_id": latest.get("proposal_id"),
            "signal": latest.get("side", "NO_TRADE"),
        },
        "risk": {
            "status": risk.get("status", "BLOCK"),
            "approved": risk.get("risk_approved", False),
            "reason_codes": risk.get("reason_codes", []),
        },
        "execution": {
            "status": execution_status,
            "reconciliation_status": latest.get("reconciliation_status", "NOT_STARTED"),
            "anomalies": sorted(set(str(item) for item in anomalies)),
            "records_count": ledger.get("records_count", 0),
            "metrics": ledger.get("metrics", {}),
        },
        "positions": safe_positions,
        "timeline": timeline,
        "demo_execution_enabled": False,
        "autonomous_demo_scope": "ODIN_AUTONOMOUS_DEMO_RC2",
        "initial_canary_complete": initial_canary_complete,
        "canary_confirmation_required": not initial_canary_complete,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _drawdown(account: dict[str, object]) -> float | None:
    balance = account.get("balance")
    equity = account.get("equity")
    if (
        not isinstance(balance, (int, float))
        or not isinstance(equity, (int, float))
        or balance <= 0
    ):
        return None
    return round(max(0.0, (float(balance) - float(equity)) / float(balance) * 100), 4)


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _execution_timeline(records: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for record in records:
        ticket = record.get("ticket")
        ticket_text = str(ticket) if isinstance(ticket, (str, int)) else ""
        result.append(
            {
                "sequence": record.get("sequence"),
                "timestamp_utc": record.get("close_time")
                or record.get("open_time")
                or record.get("timestamp"),
                "decision_id": record.get("decision_id"),
                "proposal_id": record.get("proposal_id"),
                "symbol": record.get("symbol"),
                "side": record.get("side"),
                "execution_status": record.get("execution_status"),
                "reconciliation_status": record.get("reconciliation_status"),
                "realized_pnl": record.get("realized_pnl"),
                "close_reason": record.get("close_reason"),
                "ticket_masked": f"••••{ticket_text[-4:]}" if ticket_text else None,
            }
        )
    return result

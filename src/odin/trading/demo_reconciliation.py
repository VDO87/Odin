"""Broker-truth reconciliation and restart recovery for DEMO execution."""

from __future__ import annotations

from pathlib import Path

from odin.trading.execution_ledger import read_execution_ledger


def reconcile_broker_truth(
    *,
    ledger_path: str | Path,
    broker_positions: list[dict[str, object]],
    broker_orders: list[dict[str, object]],
) -> dict[str, object]:
    """Treat MT5 snapshot as truth; discrepancies block rather than self-repair."""
    ledger = read_execution_ledger(ledger_path)
    if ledger["status"] != "OK":
        return _blocked("execution_ledger_invalid")
    latest = ledger.get("latest")
    known_active = (
        isinstance(latest, dict)
        and latest.get("execution_status") in {"SUBMITTED", "FILLED"}
    )
    known_ticket = latest.get("ticket") if isinstance(latest, dict) else None
    known_position = latest.get("position_id") if isinstance(latest, dict) else None
    if broker_positions and not known_active:
        return _blocked("unexpected_broker_position")
    if broker_orders and not known_active:
        return _blocked("unexpected_broker_order")
    if known_active:
        assert isinstance(latest, dict)
        matched_position = _find_identifier(broker_positions, known_position, "ticket", "identifier")
        matched_order = _find_identifier(broker_orders, known_ticket, "ticket", "order")
        if matched_position is None and known_position is None:
            symbol_matches = [
                item for item in broker_positions if item.get("symbol") == latest.get("symbol")
            ]
            matched_position = symbol_matches[0] if len(symbol_matches) == 1 else None
        if not matched_position and not matched_order:
            return _blocked("submitted_or_filled_not_found_at_broker")
        candidate = matched_position or matched_order
        assert isinstance(candidate, dict)
        mismatches = _position_mismatches(latest, candidate)
        if mismatches:
            return _blocked("broker_local_mismatch", details=mismatches)
    return {
        "status": "RECONCILED",
        "reason": "broker_truth_matches_local_ledger",
        "broker_positions_count": len(broker_positions),
        "broker_orders_count": len(broker_orders),
        "new_proposals_allowed": True,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def recovery_gate(
    *,
    ledger_path: str | Path,
    broker_positions: list[dict[str, object]] | None,
    broker_orders: list[dict[str, object]] | None,
    terminal_connected: bool,
) -> dict[str, object]:
    """Require a fresh MT5 query after every process/WSL restart."""
    if not terminal_connected:
        return _blocked("recovery_terminal_disconnected")
    if broker_positions is None or broker_orders is None:
        return _blocked("recovery_broker_snapshot_missing")
    result = reconcile_broker_truth(
        ledger_path=ledger_path,
        broker_positions=broker_positions,
        broker_orders=broker_orders,
    )
    return {
        **result,
        "recovery_completed": result["status"] == "RECONCILED",
        "broker_is_source_of_truth": True,
    }


def _find_identifier(
    items: list[dict[str, object]], identifier: object, *keys: str
) -> dict[str, object] | None:
    if identifier is None:
        return None
    for item in items:
        if any(item.get(key) == identifier for key in keys):
            return item
    return None


def _position_mismatches(local: dict[str, object], broker: dict[str, object]) -> list[str]:
    checks = (
        ("symbol", local.get("symbol"), broker.get("symbol")),
        ("side", local.get("side"), _broker_side(broker.get("type"))),
        ("volume", local.get("executed_volume"), broker.get("volume")),
        ("entry", local.get("executed_price"), broker.get("price_open", broker.get("price"))),
        ("stop_loss", local.get("stop_loss"), broker.get("sl")),
        ("take_profit", local.get("take_profit"), broker.get("tp")),
    )
    return [name for name, expected, observed in checks if expected is not None and expected != observed]


def _broker_side(value: object) -> object:
    if value in {0, "BUY"}:
        return "BUY"
    if value in {1, "SELL"}:
        return "SELL"
    return value


def _blocked(reason: str, *, details: list[str] | None = None) -> dict[str, object]:
    return {
        "status": "RECONCILIATION_BLOCK",
        "reason": reason,
        "details": details or [],
        "new_proposals_allowed": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }

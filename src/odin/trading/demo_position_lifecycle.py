"""Broker-truth close reconciliation for any ODIN DEMO position lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from odin.trading.execution_ledger import (
    confirm_execution_close,
    confirm_execution_reconciliation,
    read_execution_ledger,
)
from odin.trading.market_time import normalize_broker_timestamp


_ACTIVE_LEDGER_STATES = {"SUBMITTED", "FILLED", "RECONCILED"}


def reconcile_latest_broker_close(
    mt5: Any,
    *,
    ledger_path: str | Path,
    broker_positions: list[dict[str, object]],
    broker_orders: list[dict[str, object]],
    broker: str,
    server: str,
    point: float,
    now_utc: datetime | None = None,
) -> dict[str, object]:
    """Persist CLOSED only when MT5 history fully proves the latest lifecycle."""
    verified = read_execution_ledger(ledger_path)
    if verified.get("status") != "OK":
        return _blocked("execution_ledger_invalid")
    latest = verified.get("latest")
    if not isinstance(latest, dict):
        return _status("NO_CHANGE", "execution_ledger_empty")
    ledger_state = latest.get("execution_status")
    if ledger_state == "CLOSED":
        return _status("ALREADY_CLOSED", "latest_lifecycle_already_closed")
    if ledger_state not in _ACTIVE_LEDGER_STATES:
        return _status("NO_CHANGE", "latest_lifecycle_not_open")
    position_id = _integer(latest.get("position_id"))
    position_id_recovered = False
    if position_id <= 0:
        recovered = _recover_position_id_from_submission_history(mt5, latest)
        if recovered.get("status") != "RECOVERED":
            return _blocked(str(recovered.get("reason", "active_lifecycle_position_id_missing")))
        position_id = _integer(recovered.get("position_id"))
        position_id_recovered = True
    if _contains_position(broker_positions, position_id):
        return _status("POSITION_OPEN", "broker_position_still_open")
    if _contains_order(broker_orders, position_id):
        return _status("ORDER_PENDING", "broker_order_still_pending")

    history_deals_value = mt5.history_deals_get(position=position_id)
    history_orders_value = mt5.history_orders_get(position=position_id)
    if history_deals_value is None or history_orders_value is None:
        return _blocked("broker_lifecycle_history_unavailable")
    deals = [_mapping(item) for item in history_deals_value]
    orders = [_mapping(item) for item in history_orders_value]
    entry_in = getattr(mt5, "DEAL_ENTRY_IN", 0)
    exit_entries = {
        getattr(mt5, "DEAL_ENTRY_OUT", 1),
        getattr(mt5, "DEAL_ENTRY_OUT_BY", 3),
    }
    entry_deals = [
        deal
        for deal in deals
        if _integer(deal.get("position_id")) == position_id
        and _integer(deal.get("entry")) == entry_in
    ]
    exit_deals = [
        deal
        for deal in deals
        if _integer(deal.get("position_id")) == position_id
        and _integer(deal.get("entry")) in exit_entries
    ]
    if not entry_deals or not exit_deals:
        return _blocked("broker_close_history_incomplete")
    requested_volume = _number(latest.get("executed_volume"))
    entry_volume = round(sum(_number(item.get("volume")) for item in entry_deals), 8)
    exit_volume = round(sum(_number(item.get("volume")) for item in exit_deals), 8)
    if requested_volume <= 0 or entry_volume != requested_volume or exit_volume != requested_volume:
        return _blocked("broker_close_volume_mismatch")
    order_tickets = {_integer(item.get("ticket")) for item in orders}
    close_order_ids = {_integer(item.get("order")) for item in exit_deals}
    if 0 in close_order_ids or not close_order_ids.issubset(order_tickets):
        return _blocked("broker_close_order_missing")
    latest_exit = max(exit_deals, key=lambda item: _integer(item.get("time_msc")))
    current = (now_utc or datetime.now(UTC)).astimezone(UTC)
    close_time = normalize_broker_timestamp(
        latest_exit.get("time"), now_utc=current, broker=broker, server=server
    )
    if close_time.status == "BLOCKED" or close_time.normalized_event_time_utc is None:
        return _blocked("broker_close_time_normalization_blocked")
    exit_price = _weighted_price(exit_deals)
    if exit_price <= 0:
        return _blocked("broker_close_price_invalid")
    commission = sum(_number(item.get("commission")) for item in deals)
    swap = sum(_number(item.get("swap")) for item in deals)
    fee = sum(_number(item.get("fee")) for item in deals)
    profit = sum(_number(item.get("profit")) for item in deals)
    realized_pnl = round(profit + commission + swap + fee, 2)
    close_reason = _close_reason(mt5, latest_exit.get("reason"))
    stop_loss = _number(latest.get("stop_loss"))
    exit_slippage_points = (
        abs(exit_price - stop_loss) / point
        if close_reason == "SL" and point > 0 and stop_loss > 0
        else None
    )
    raw_evidence = {
        "position_id": position_id,
        "entry_deal_ids": sorted(_integer(item.get("ticket")) for item in entry_deals),
        "exit_deal_ids": sorted(_integer(item.get("ticket")) for item in exit_deals),
        "close_order_ids": sorted(close_order_ids),
        "entry_volume": entry_volume,
        "exit_volume": exit_volume,
        "observed_at_utc": current.isoformat(),
    }
    evidence_hash = hashlib.sha256(
        json.dumps(raw_evidence, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if (
        latest.get("execution_status") in {"SUBMITTED", "FILLED"}
        and latest.get("reconciliation_status") == "PENDING"
    ):
        reconciled = confirm_execution_reconciliation(
            path=ledger_path,
            proposal_id=str(latest.get("proposal_id", "")),
            reconciliation_result={
                "status": "RECONCILED",
                "broker_is_source_of_truth": True,
                "reason": "broker_history_proved_submission_lifecycle",
            },
            position_id=position_id,
        )
        if reconciled.get("status") not in {"RECONCILED", "ALREADY_RECONCILED"}:
            return _blocked("execution_ledger_reconciliation_blocked")
    result = confirm_execution_close(
        path=ledger_path,
        proposal_id=str(latest.get("proposal_id", "")),
        close_evidence={
            "status": "CLOSED",
            "broker_is_source_of_truth": True,
            "position_open": False,
            "pending_order": False,
            "position_id": position_id,
            "volume": exit_volume,
            "exit_price": exit_price,
            "close_time_utc": close_time.normalized_event_time_utc,
            "realized_pnl": realized_pnl,
            "close_reason": close_reason,
            "close_order_id": max(close_order_ids),
            "close_deal_id": _integer(latest_exit.get("ticket")),
            "commission": round(commission, 2),
            "swap": round(swap, 2),
            "fee": round(fee, 2),
            "exit_slippage_points": exit_slippage_points,
            "evidence_hash": evidence_hash,
        },
    )
    if result.get("status") not in {"CLOSED", "ALREADY_CLOSED"}:
        return _blocked("execution_ledger_close_blocked")
    return {
        "status": "CLOSED_AND_RECONCILED",
        "reason": "broker_history_proved_close",
        "proposal_id": latest.get("proposal_id"),
        "position_id": position_id,
        "close_time_utc": close_time.normalized_event_time_utc,
        "close_reason": close_reason,
        "realized_pnl": realized_pnl,
        "evidence_hash": evidence_hash,
        "position_id_recovered": position_id_recovered,
        "broker_submission_called": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _recover_position_id_from_submission_history(
    mt5: Any, latest: dict[str, object]
) -> dict[str, object]:
    """Recover one broker position id from exact persisted submission identifiers."""
    submission = latest.get("order_send_result")
    if not isinstance(submission, dict):
        return _recovery_block("active_lifecycle_submission_evidence_missing")
    deal_ticket = _integer(submission.get("deal"))
    order_ticket = _integer(submission.get("order"))
    ledger_ticket = _integer(latest.get("ticket"))
    if deal_ticket <= 0 or order_ticket <= 0 or ledger_ticket != order_ticket:
        return _recovery_block("active_lifecycle_submission_identifiers_invalid")

    deals_value = mt5.history_deals_get(ticket=deal_ticket)
    orders_value = mt5.history_orders_get(ticket=order_ticket)
    if deals_value is None or orders_value is None:
        return _recovery_block("broker_submission_history_unavailable")
    deals = [_mapping(item) for item in deals_value]
    orders = [_mapping(item) for item in orders_value]
    if len(deals) != 1 or len(orders) != 1:
        return _recovery_block("broker_submission_history_not_unique")
    deal = deals[0]
    order = orders[0]

    proposal_id = latest.get("proposal_id")
    expected_symbol = latest.get("broker_symbol")
    expected_side = latest.get("side")
    expected_volume = _number(latest.get("executed_volume"))
    if not isinstance(proposal_id, str) or not proposal_id:
        return _recovery_block("active_lifecycle_proposal_id_missing")
    expected_magic = int(hashlib.sha256(proposal_id.encode()).hexdigest()[:8], 16)
    expected_comment = f"ODIN_RC2_{proposal_id[:12]}"
    expected_type = (
        getattr(mt5, "DEAL_TYPE_BUY", 0)
        if expected_side == "BUY"
        else getattr(mt5, "DEAL_TYPE_SELL", 1)
        if expected_side == "SELL"
        else None
    )
    expected_order_type = (
        getattr(mt5, "ORDER_TYPE_BUY", 0)
        if expected_side == "BUY"
        else getattr(mt5, "ORDER_TYPE_SELL", 1)
        if expected_side == "SELL"
        else None
    )
    position_ids = {
        _integer(deal.get("position_id")),
        _integer(order.get("position_id")),
    }
    position_ids.discard(0)
    checks = (
        _integer(deal.get("ticket")) == deal_ticket,
        _integer(deal.get("order")) == order_ticket,
        _integer(order.get("ticket")) == order_ticket,
        len(position_ids) == 1,
        deal.get("symbol") == expected_symbol,
        order.get("symbol") == expected_symbol,
        expected_type is not None and _integer(deal.get("type")) == expected_type,
        expected_order_type is not None and _integer(order.get("type")) == expected_order_type,
        _integer(deal.get("entry")) == getattr(mt5, "DEAL_ENTRY_IN", 0),
        expected_volume > 0 and _number(deal.get("volume")) == expected_volume,
        _number(order.get("volume_initial")) == expected_volume,
        _integer(order.get("state")) == getattr(mt5, "ORDER_STATE_FILLED", 4),
        _integer(deal.get("magic")) == expected_magic,
        _integer(order.get("magic")) == expected_magic,
        deal.get("comment") == expected_comment,
        order.get("comment") == expected_comment,
    )
    if not all(checks):
        return _recovery_block("broker_submission_history_mismatch")
    return {
        "status": "RECOVERED",
        "reason": "position_id_recovered_from_exact_submission_history",
        "position_id": next(iter(position_ids)),
        "broker_submission_called": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _contains_position(items: list[dict[str, object]], position_id: int) -> bool:
    return any(
        position_id in {_integer(item.get("ticket")), _integer(item.get("identifier"))}
        for item in items
    )


def _contains_order(items: list[dict[str, object]], position_id: int) -> bool:
    return any(
        position_id
        in {
            _integer(item.get("position_id")),
            _integer(item.get("position_by_id")),
        }
        for item in items
    )


def _mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    asdict = getattr(value, "_asdict", None)
    return dict(asdict()) if callable(asdict) else {}


def _weighted_price(items: list[dict[str, object]]) -> float:
    volume = sum(_number(item.get("volume")) for item in items)
    if volume <= 0:
        return 0.0
    return sum(_number(item.get("price")) * _number(item.get("volume")) for item in items) / volume


def _close_reason(mt5: Any, value: object) -> str:
    mapping = {
        getattr(mt5, "DEAL_REASON_SL", -1001): "SL",
        getattr(mt5, "DEAL_REASON_TP", -1002): "TP",
        getattr(mt5, "DEAL_REASON_CLIENT", -1003): "MANUAL_CLIENT",
        getattr(mt5, "DEAL_REASON_EXPERT", -1004): "EXPERT",
        getattr(mt5, "DEAL_REASON_SO", -1005): "STOP_OUT",
    }
    return mapping.get(value, "BROKER_OTHER")


def _number(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _integer(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) else 0


def _status(status: str, reason: str) -> dict[str, object]:
    return {
        "status": status,
        "reason": reason,
        "broker_submission_called": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _blocked(reason: str) -> dict[str, object]:
    return _status("RECONCILIATION_BLOCK", reason)


def _recovery_block(reason: str) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "reason": reason,
        "broker_submission_called": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }

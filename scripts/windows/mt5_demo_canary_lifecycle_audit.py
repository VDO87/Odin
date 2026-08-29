"""Read MT5 history and close the first DEMO CANARY audit trail append-only."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.environ["ODIN_RC1_REPO_SRC"])

import MetaTrader5 as mt5  # type: ignore[import-not-found]  # noqa: E402

from odin.trading.demo_decision_ledger import (  # noqa: E402
    append_demo_decision,
    read_demo_decision_ledger,
)
from odin.trading.execution_ledger import (  # noqa: E402
    confirm_execution_close,
    read_execution_ledger,
)
from odin.trading.market_time import (  # noqa: E402
    assess_market_timestamp,
    normalize_broker_timestamp,
)


EXPECTED_BROKER = "OANDA TMS Brokers S.A."
BROKER_SYMBOL = "EURUSD.pro"


def main() -> int:
    report_path = Path(os.environ["ODIN_RC1_AUDIT_REPORT_PATH"])
    terminal_path = os.environ["ODIN_RC1_TERMINAL_PATH"]
    canary_path = Path(os.environ["ODIN_RC1_CANARY_REPORT_PATH"])
    execution_path = Path(os.environ["ODIN_RC1_LEDGER_PATH"])
    decision_path = Path(os.environ["ODIN_RC1_DECISION_LEDGER_PATH"])
    canary = _load_json(canary_path)
    if not _valid_canary(canary):
        return _finish(report_path, _blocked("validated_canary_report_required"))

    connected = mt5.initialize(terminal_path, timeout=120_000)
    try:
        if not connected:
            code, description = mt5.last_error()
            return _finish(
                report_path,
                _blocked(
                    "initialize_failed",
                    last_error={"code": code, "description": description},
                ),
            )
        account = _mapping(mt5.account_info())
        terminal = _mapping(mt5.terminal_info())
        symbol = _mapping(mt5.symbol_info(BROKER_SYMBOL))
        tick = _mapping(mt5.symbol_info_tick(BROKER_SYMBOL))
        if not all((account, terminal, symbol, tick)):
            return _finish(report_path, _blocked("mt5_audit_evidence_missing"))
        identity_reasons = _identity_reasons(
            account=account,
            terminal=terminal,
            terminal_path=terminal_path,
        )
        if identity_reasons:
            return _finish(
                report_path,
                _blocked("account_identity_hard_block", reason_codes=identity_reasons),
            )

        position_id = _integer(canary.get("order"))
        if position_id <= 0:
            return _finish(report_path, _blocked("canary_position_id_missing"))
        positions_value = mt5.positions_get(symbol=BROKER_SYMBOL)
        orders_value = mt5.orders_get(symbol=BROKER_SYMBOL)
        history_orders_value = mt5.history_orders_get(position=position_id)
        history_deals_value = mt5.history_deals_get(position=position_id)
        if any(
            value is None
            for value in (
                positions_value,
                orders_value,
                history_orders_value,
                history_deals_value,
            )
        ):
            return _finish(report_path, _blocked("broker_history_snapshot_unavailable"))
        positions = [_mapping(value) for value in positions_value or ()]
        orders = [_mapping(value) for value in orders_value or ()]
        history_orders = [_mapping(value) for value in history_orders_value or ()]
        history_deals = [_mapping(value) for value in history_deals_value or ()]

        result = _audit_and_reconcile(
            canary=canary,
            canary_path=canary_path,
            execution_path=execution_path,
            decision_path=decision_path,
            account=account,
            terminal=terminal,
            symbol=symbol,
            tick=tick,
            positions=positions,
            orders=orders,
            history_orders=history_orders,
            history_deals=history_deals,
        )
        return _finish(report_path, result)
    finally:
        mt5.shutdown()


def _audit_and_reconcile(
    *,
    canary: dict[str, object],
    canary_path: Path,
    execution_path: Path,
    decision_path: Path,
    account: dict[str, object],
    terminal: dict[str, object],
    symbol: dict[str, object],
    tick: dict[str, object],
    positions: list[dict[str, object]],
    orders: list[dict[str, object]],
    history_orders: list[dict[str, object]],
    history_deals: list[dict[str, object]],
) -> dict[str, object]:
    now = datetime.now(UTC)
    broker = str(account.get("company", ""))
    server = str(account.get("server", ""))
    position_id = _integer(canary.get("order"))
    entry_deals = [
        deal
        for deal in history_deals
        if _integer(deal.get("position_id")) == position_id
        and deal.get("entry") == getattr(mt5, "DEAL_ENTRY_IN", 0)
    ]
    exit_deals = [
        deal
        for deal in history_deals
        if _integer(deal.get("position_id")) == position_id
        and deal.get("entry") in {
            getattr(mt5, "DEAL_ENTRY_OUT", 1),
            getattr(mt5, "DEAL_ENTRY_OUT_BY", 3),
        }
    ]
    position_open = any(
        position_id in {_integer(item.get("ticket")), _integer(item.get("identifier"))}
        for item in positions
    )
    pending_order = any(
        position_id
        in {
            _integer(item.get("position_id")),
            _integer(item.get("position_by_id")),
        }
        for item in orders
    )
    history_tickets = {_integer(item.get("ticket")) for item in history_orders}
    if (
        len(entry_deals) != 1
        or len(exit_deals) != 1
        or position_open
        or pending_order
        or position_id not in history_tickets
    ):
        return _blocked(
            "canary_history_not_complete",
            reason_codes=("reconciliation_mismatch",),
        )

    entry = entry_deals[0]
    exit_deal = exit_deals[0]
    close_order_id = _integer(exit_deal.get("order"))
    if close_order_id not in history_tickets:
        return _blocked("canary_close_order_missing")
    volume = _number(entry.get("volume"))
    if volume != _number(canary.get("executed_volume")) or volume != _number(
        exit_deal.get("volume")
    ):
        return _blocked("canary_history_volume_mismatch")
    if _number(entry.get("price")) != _number(canary.get("executed_price")):
        return _blocked("canary_entry_price_mismatch")

    entry_time = normalize_broker_timestamp(
        entry.get("time"), now_utc=now, broker=broker, server=server
    )
    close_time = normalize_broker_timestamp(
        exit_deal.get("time"), now_utc=now, broker=broker, server=server
    )
    current_market_time = assess_market_timestamp(
        tick.get("time"), now_utc=now, broker=broker, server=server
    )
    if (
        entry_time.status == "BLOCKED"
        or close_time.status == "BLOCKED"
        or entry_time.normalized_event_time_utc is None
        or close_time.normalized_event_time_utc is None
    ):
        return _blocked("canary_history_time_normalization_blocked")

    execution_before = read_execution_ledger(execution_path)
    latest = execution_before.get("latest")
    if (
        execution_before.get("status") != "OK"
        or not isinstance(latest, dict)
        or latest.get("proposal_id") != canary.get("proposal_id")
        or latest.get("decision_id") != canary.get("decision_id")
        or latest.get("position_id") != position_id
        or latest.get("execution_status") not in {"RECONCILED", "CLOSED"}
    ):
        return _blocked("execution_ledger_canary_mismatch")

    raw_evidence = {
        "canary_report_sha256": _sha256(canary_path),
        "position_id": position_id,
        "entry_deal": _deal_evidence(entry),
        "exit_deal": _deal_evidence(exit_deal),
        "history_order_tickets": sorted(history_tickets),
        "position_open": position_open,
        "pending_order": pending_order,
        "observed_at_utc": now.isoformat(),
    }
    evidence_hash = hashlib.sha256(
        json.dumps(raw_evidence, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    point = _number(symbol.get("point"))
    stop_loss = _number(canary.get("sl"))
    exit_price = _number(exit_deal.get("price"))
    commission = sum(_number(deal.get("commission")) for deal in history_deals)
    swap = sum(_number(deal.get("swap")) for deal in history_deals)
    fee = sum(_number(deal.get("fee")) for deal in history_deals)
    profit = sum(_number(deal.get("profit")) for deal in history_deals)
    realized_pnl = round(profit + commission + swap + fee, 2)
    close_reason = _close_reason(exit_deal.get("reason"))
    exit_slippage_points = (
        abs(exit_price - stop_loss) / point if close_reason == "SL" and point > 0 else None
    )

    decision_result = append_demo_decision(
        path=decision_path,
        retrospective=True,
        decision={
            "schema": "odin.demo_execution_decision/v1",
            "decision_id": canary.get("decision_id"),
            "proposal_id": canary.get("proposal_id"),
            "decision_timestamp_utc": latest.get("timestamp"),
            "decision_status": "CANARY_EXECUTED_RETROSPECTIVE_AUDIT",
            "retrospective": True,
            "source_canary_report_sha256": raw_evidence["canary_report_sha256"],
            "human_confirmation": canary.get("human_confirmation"),
            "original_broker_submission_called": True,
            "account_mode": "DEMO",
            "broker": broker,
            "server": server,
            "symbol": canary.get("symbol"),
            "broker_symbol": canary.get("broker_symbol"),
            "side": canary.get("side"),
            "volume": canary.get("volume"),
            "risk_status": canary.get("risk_status"),
            "execution_allowed": False,
            "safe_to_trade": False,
            "real_trading": False,
        },
    )
    if decision_result.get("status") not in {"RECORDED", "ALREADY_RECORDED"}:
        return _blocked("demo_decision_ledger_blocked")

    close_result = confirm_execution_close(
        path=execution_path,
        proposal_id=str(canary.get("proposal_id", "")),
        close_evidence={
            "status": "CLOSED",
            "broker_is_source_of_truth": True,
            "position_open": False,
            "pending_order": False,
            "position_id": position_id,
            "volume": volume,
            "exit_price": exit_price,
            "close_time_utc": close_time.normalized_event_time_utc,
            "realized_pnl": realized_pnl,
            "close_reason": close_reason,
            "close_order_id": close_order_id,
            "close_deal_id": _integer(exit_deal.get("ticket")),
            "commission": commission,
            "swap": swap,
            "fee": fee,
            "exit_slippage_points": exit_slippage_points,
            "evidence_hash": evidence_hash,
        },
    )
    if close_result.get("status") not in {"CLOSED", "ALREADY_CLOSED"}:
        return _blocked("execution_ledger_close_blocked")

    execution_after = read_execution_ledger(execution_path)
    decision_after = read_demo_decision_ledger(decision_path)
    if execution_after.get("status") != "OK" or decision_after.get("status") != "OK":
        return _blocked("ledger_integrity_after_close_failed")
    latest_after = execution_after.get("latest")
    if not isinstance(latest_after, dict) or latest_after.get("execution_status") != "CLOSED":
        return _blocked("execution_ledger_close_not_persisted")

    entry_reference = _number(canary.get("entry_reference"))
    entry_price = _number(entry.get("price"))
    spread_price = _number(latest.get("spread"))
    return {
        "schema": "odin.demo_canary_lifecycle_audit/v1",
        "status": "COMPLETE_AND_RECONCILED",
        "canary_position": "CLOSED",
        "canary_lifecycle": "COMPLETE_AND_RECONCILED",
        "entry": {
            "deal_id": _integer(entry.get("ticket")),
            "order_id": _integer(entry.get("order")),
            "position_id": position_id,
            "raw_broker_time": entry.get("time"),
            "normalized_time_utc": entry_time.normalized_event_time_utc,
            "price": entry_price,
            "volume": volume,
            "sl": canary.get("sl"),
            "tp": canary.get("tp"),
            "spread_price": spread_price,
            "spread_points": spread_price / point if point > 0 else None,
            "slippage_points": abs(entry_price - entry_reference) / point
            if point > 0
            else None,
        },
        "exit": {
            "deal_id": _integer(exit_deal.get("ticket")),
            "order_id": close_order_id,
            "raw_broker_time": exit_deal.get("time"),
            "normalized_time_utc": close_time.normalized_event_time_utc,
            "price": exit_price,
            "volume": volume,
            "reason": close_reason,
            "slippage_points": exit_slippage_points,
        },
        "realized_pnl": realized_pnl,
        "profit": profit,
        "commission": commission,
        "swap": swap,
        "fee": fee,
        "mt5_ledger": "RECONCILED",
        "decision_ledger": "RECONCILED",
        "time_profile": {
            "status": "VALID"
            if current_market_time.normalization_confidence == "HIGH"
            else "BLOCKED",
            "profile": current_market_time.source_profile,
            "raw_broker_time": current_market_time.tick_time_raw,
            "raw_datetime_as_utc": current_market_time.tick_time_utc,
            "expected_cet_cest_offset_seconds": current_market_time.expected_server_offset_seconds,
            "normalized_utc": current_market_time.normalized_event_time_utc,
            "data_age_seconds": current_market_time.age_seconds,
            "freshness": current_market_time.status,
            "reason_codes": list(current_market_time.reason_codes),
            "normalization_method": current_market_time.normalization_method,
            "normalization_confidence": current_market_time.normalization_confidence,
        },
        "terminal": {
            "path": terminal.get("path"),
            "connected": terminal.get("connected") is True,
            "terminal_trade_allowed": (
                terminal.get("trade_allowed") is True
                and terminal.get("tradeapi_disabled") is not True
                and account.get("trade_allowed") is True
            ),
            "terminal_trade_allowed_raw": terminal.get("trade_allowed") is True,
            "terminal_tradeapi_disabled": terminal.get("tradeapi_disabled") is True,
            "account_trade_allowed": account.get("trade_allowed") is True,
            "account_trade_expert": account.get("trade_expert") is True,
        },
        "provenance": {
            **raw_evidence,
            "evidence_hash": evidence_hash,
            "execution_ledger_sha256": _sha256(execution_path),
            "decision_ledger_sha256": _sha256(decision_path),
        },
        "broker_submission_called": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }


def _identity_reasons(
    *,
    account: dict[str, object],
    terminal: dict[str, object],
    terminal_path: str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    expected_parent = str(Path(terminal_path).parent).lower()
    if str(terminal.get("path", "")).lower() != expected_parent:
        reasons.append("terminal_path_mismatch")
    if terminal.get("connected") is not True:
        reasons.append("terminal_not_connected")
    if account.get("trade_mode") != getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0):
        reasons.append("account_not_demo")
    if str(account.get("company", "")) != EXPECTED_BROKER:
        reasons.append("broker_mismatch")
    if str(account.get("server", "")) != os.environ["ODIN_RC1_EXPECTED_SERVER"]:
        reasons.append("server_mismatch")
    if str(account.get("login", "")) != os.environ["ODIN_RC1_EXPECTED_LOGIN"]:
        reasons.append("login_mismatch")
    return tuple(reasons)


def _valid_canary(canary: dict[str, object]) -> bool:
    return (
        canary.get("status") == "CANARY_SUBMITTED_AND_RECONCILED"
        and canary.get("account") == "DEMO"
        and canary.get("broker") == EXPECTED_BROKER
        and canary.get("server") == "OANDATMS-MT5"
        and canary.get("broker_submission_called") is True
        and canary.get("real_trading") is False
        and canary.get("execution_allowed") is False
    )


def _deal_evidence(deal: dict[str, object]) -> dict[str, object]:
    return {
        key: deal.get(key)
        for key in (
            "ticket",
            "order",
            "position_id",
            "time",
            "time_msc",
            "type",
            "entry",
            "reason",
            "volume",
            "price",
            "commission",
            "swap",
            "profit",
            "fee",
            "symbol",
            "comment",
        )
    }


def _close_reason(value: object) -> str:
    mapping = {
        getattr(mt5, "DEAL_REASON_SL", 4): "SL",
        getattr(mt5, "DEAL_REASON_TP", 5): "TP",
        getattr(mt5, "DEAL_REASON_CLIENT", 0): "MANUAL_CLIENT",
        getattr(mt5, "DEAL_REASON_MOBILE", 1): "MANUAL_MOBILE",
        getattr(mt5, "DEAL_REASON_WEB", 2): "MANUAL_WEB",
        getattr(mt5, "DEAL_REASON_EXPERT", 3): "EXPERT",
        getattr(mt5, "DEAL_REASON_SO", 6): "STOP_OUT",
    }
    return mapping.get(value, f"OTHER_{value}")


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _mapping(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    method = getattr(value, "_asdict", None)
    return method() if callable(method) else {}


def _number(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _integer(value: object) -> int:
    return int(value) if isinstance(value, (int, float)) else 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _blocked(
    reason: str,
    *,
    reason_codes: tuple[str, ...] | list[str] | None = None,
    last_error: dict[str, object] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "schema": "odin.demo_canary_lifecycle_audit/v1",
        "status": "RECONCILIATION_BLOCK",
        "reason": reason,
        "reason_codes": list(reason_codes or (reason,)),
        "canary_lifecycle": "RECONCILIATION_BLOCK",
        "broker_submission_called": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }
    if last_error is not None:
        result["last_error"] = last_error
    return result


def _finish(path: Path, result: dict[str, object]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "COMPLETE_AND_RECONCILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())

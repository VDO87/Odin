"""Single, isolated MT5 DEMO execution boundary for RC1.

The module is dependency-injected so offline tests never import or contact the
MetaTrader5 runtime.  The only order submission call in ODIN is intentionally
visible here and remains unreachable without a CANARY_READY gate result.
"""

from __future__ import annotations

import hashlib
from typing import Any

from odin.contracts.demo_execution import DemoAccountEvidence, DemoRiskLimits, TradeProposal
from odin.contracts.events import redact_for_audit


def perform_order_check(
    mt5: Any,
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    gate_result: dict[str, object],
    *,
    limits: DemoRiskLimits | None = None,
) -> dict[str, object]:
    """Run one broker-side validation; this function cannot submit an order."""
    if gate_result.get("order_check_allowed") is not True:
        return _blocked("demo_gate_did_not_allow_order_check")
    identity_reasons = _live_identity_blocks(mt5, evidence)
    if identity_reasons:
        return _hard_block(identity_reasons)
    request_result = _build_request(mt5, proposal, evidence, limits or DemoRiskLimits())
    if request_result["status"] != "OK":
        return request_result
    request = request_result["request"]
    assert isinstance(request, dict)
    result = mt5.order_check(request)
    if result is None:
        return _blocked("order_check_no_result", last_error=_last_error(mt5))
    sanitized = _sanitize_result(result)
    if sanitized.get("retcode") != 0:
        return {
            **_blocked(_classify_retcode(mt5, sanitized.get("retcode"), check=True)),
            "order_check_result": sanitized,
            "request": _sanitize_request(request),
        }
    return {
        "status": "ORDER_CHECKED",
        "accepted": True,
        "request": _sanitize_request(request),
        "order_check_result": sanitized,
        "order_send_allowed": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def submit_demo_canary(
    mt5: Any,
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    gate_result: dict[str, object],
    checked: dict[str, object],
    submission_reservation: dict[str, object],
) -> dict[str, object]:
    """Submit exactly once after a one-shot human-gated DEMO authorization."""
    gate_reasons = []
    required = {
        "status": "CANARY_READY",
        "demo_execution_enabled": True,
        "order_send_allowed": True,
        "account_is_demo": True,
        "risk_approved": True,
        "reconciliation_ok": True,
        "real_trading": False,
        "execution_allowed": False,
    }
    for key, expected in required.items():
        if gate_result.get(key) != expected:
            gate_reasons.append(f"gate_{key}_invalid")
    if checked.get("status") != "ORDER_CHECKED" or checked.get("accepted") is not True:
        gate_reasons.append("order_check_not_accepted")
    expected_proposal_hash = hashlib.sha256(proposal.proposal_id.encode()).hexdigest()
    if (
        submission_reservation.get("status") != "RESERVED"
        or submission_reservation.get("reserved") is not True
        or submission_reservation.get("proposal_hash") != expected_proposal_hash
    ):
        gate_reasons.append("submission_not_atomically_reserved")
    if gate_reasons:
        return {
            **_blocked("canary_gate_invalid", reason_codes=gate_reasons),
            "order_send_called": False,
        }
    identity_reasons = _live_identity_blocks(mt5, evidence)
    if identity_reasons:
        return {**_hard_block(identity_reasons), "order_send_called": False}
    request = checked.get("request")
    if not isinstance(request, dict):
        return {**_blocked("checked_request_missing"), "order_send_called": False}
    result = mt5.order_send(request)
    if result is None:
        return {
            **_blocked("order_send_unknown_result", last_error=_last_error(mt5)),
            "order_send_called": True,
        }
    sanitized = _sanitize_result(result)
    retcode = sanitized.get("retcode")
    status = _submission_status(mt5, retcode)
    return {
        "status": status,
        "reason": _submission_reason(mt5, retcode),
        "order_send_result": sanitized,
        "request": _sanitize_request(request),
        "retry_allowed": False,
        "requires_reconciliation": True,
        "order_send_called": True,
        "execution_allowed_scope": "DEMO_CANARY_ONE_SHOT",
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def read_broker_execution_state(mt5: Any, evidence: DemoAccountEvidence) -> dict[str, object]:
    """Read current DEMO positions/orders for mandatory reconciliation."""
    identity_reasons = _live_identity_blocks(mt5, evidence)
    if identity_reasons:
        return _hard_block(identity_reasons)
    positions_value = mt5.positions_get()
    orders_value = mt5.orders_get()
    if positions_value is None or orders_value is None:
        return _blocked("broker_execution_snapshot_unavailable", last_error=_last_error(mt5))
    positions = [_sanitize_position(item) for item in positions_value]
    orders = [_sanitize_order(item) for item in orders_value]
    return {
        "status": "OK",
        "positions": positions,
        "orders": orders,
        "broker_is_source_of_truth": True,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _live_identity_blocks(mt5: Any, evidence: DemoAccountEvidence) -> list[str]:
    account = _as_mapping(mt5.account_info())
    terminal = _as_mapping(mt5.terminal_info())
    symbol = _as_mapping(mt5.symbol_info(evidence.broker_symbol))
    if not account or not terminal or not symbol:
        return ["live_account_or_terminal_unavailable"]
    reasons: list[str] = []
    demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
    if account.get("trade_mode") != demo_mode:
        reasons.append("live_account_not_demo")
    comparisons = (
        ("broker", str(account.get("company", "")), evidence.broker),
        ("server", str(account.get("server", "")), evidence.server),
        ("login", str(account.get("login", "")), evidence.login),
        ("terminal", str(terminal.get("path", "")), evidence.terminal_path),
    )
    for name, observed, expected in comparisons:
        if not observed or observed != expected:
            reasons.append(f"live_{name}_identity_mismatch")
    if terminal.get("connected") is not True:
        reasons.append("live_terminal_disconnected")
    if terminal.get("trade_allowed") is not True or terminal.get("tradeapi_disabled") is True:
        reasons.append("live_terminal_trading_not_allowed")
    if account.get("trade_allowed") is not True or account.get("trade_expert") is not True:
        reasons.append("live_account_trading_not_allowed")
    if symbol.get("name") != evidence.broker_symbol:
        reasons.append("live_broker_symbol_identity_mismatch")
    if symbol.get("trade_mode") == getattr(mt5, "SYMBOL_TRADE_MODE_DISABLED", 0):
        reasons.append("live_broker_symbol_not_tradable")
    return reasons


def _build_request(
    mt5: Any,
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    limits: DemoRiskLimits,
) -> dict[str, object]:
    symbol_info = _as_mapping(mt5.symbol_info(evidence.broker_symbol))
    tick = _as_mapping(mt5.symbol_info_tick(evidence.broker_symbol))
    if not symbol_info or not tick:
        return _blocked("symbol_or_tick_unavailable")
    expected_side = getattr(mt5, "ORDER_TYPE_BUY", 0) if proposal.side == "BUY" else getattr(mt5, "ORDER_TYPE_SELL", 1)
    price_key = "ask" if proposal.side == "BUY" else "bid"
    price = tick.get(price_key)
    if not isinstance(price, (int, float)) or price <= 0:
        return _blocked("bad_price")
    point = symbol_info.get("point")
    if not isinstance(point, (int, float)) or point <= 0:
        return _blocked("symbol_point_invalid")
    slippage_points = abs(float(price) - proposal.entry_reference) / float(point)
    if slippage_points > limits.maximum_execution_slippage_points:
        return _blocked("price_changed")
    filling_mode = _select_order_filling_mode(mt5, symbol_info)
    if filling_mode is None:
        return _blocked("filling_mode_error")
    magic = int(hashlib.sha256(proposal.proposal_id.encode()).hexdigest()[:8], 16)
    request = {
        "action": getattr(mt5, "TRADE_ACTION_DEAL"),
        "symbol": evidence.broker_symbol,
        "volume": proposal.volume,
        "type": expected_side,
        "price": round(float(price), evidence.digits),
        "sl": round(proposal.stop_loss, evidence.digits),
        "tp": round(proposal.take_profit, evidence.digits),
        "deviation": limits.maximum_execution_slippage_points,
        "magic": magic,
        "comment": f"ODIN_RC1_{proposal.proposal_id[:12]}",
        "type_time": getattr(mt5, "ORDER_TIME_GTC"),
        "type_filling": filling_mode,
    }
    return {"status": "OK", "request": request}


def _select_order_filling_mode(
    mt5: Any, symbol_info: dict[str, object]
) -> int | None:
    """Map SYMBOL_FILLING_MODE flags to an ORDER_FILLING_* request value."""
    raw_flags = symbol_info.get("filling_mode")
    execution_mode = symbol_info.get("trade_exemode")
    if not isinstance(raw_flags, int) or not isinstance(execution_mode, int):
        return None

    # MetaTrader documents SYMBOL_FILLING_MODE as a bitmask: FOK=1, IOC=2.
    # ORDER_FILLING_* is a separate enum: FOK=0, IOC=1, RETURN=2. Prefer
    # FOK when available so a bounded canary cannot be partially filled.
    if raw_flags & 1:
        return int(getattr(mt5, "ORDER_FILLING_FOK", 0))
    if raw_flags & 2:
        return int(getattr(mt5, "ORDER_FILLING_IOC", 1))

    market_execution = int(getattr(mt5, "SYMBOL_TRADE_EXECUTION_MARKET", 2))
    if execution_mode != market_execution:
        return int(getattr(mt5, "ORDER_FILLING_RETURN", 2))
    return None


def _submission_status(mt5: Any, retcode: object) -> str:
    if retcode == getattr(mt5, "TRADE_RETCODE_DONE", 10009):
        return "FILLED"
    if retcode == getattr(mt5, "TRADE_RETCODE_PLACED", 10008):
        return "SUBMITTED"
    return "REJECTED"


def _submission_reason(mt5: Any, retcode: object) -> str:
    if retcode == getattr(mt5, "TRADE_RETCODE_DONE", 10009):
        return "filled"
    if retcode == getattr(mt5, "TRADE_RETCODE_PLACED", 10008):
        return "placed"
    return _classify_retcode(mt5, retcode)


def _classify_retcode(mt5: Any, retcode: object, *, check: bool = False) -> str:
    mapping = {
        getattr(mt5, "TRADE_RETCODE_REJECT", 10006): "order_rejected",
        getattr(mt5, "TRADE_RETCODE_INVALID_VOLUME", 10014): "invalid_volume",
        getattr(mt5, "TRADE_RETCODE_INVALID_STOPS", 10016): "invalid_stops",
        getattr(mt5, "TRADE_RETCODE_NO_MONEY", 10019): "insufficient_margin",
        getattr(mt5, "TRADE_RETCODE_MARKET_CLOSED", 10018): "market_closed",
        getattr(mt5, "TRADE_RETCODE_REQUOTE", 10004): "requote",
        getattr(mt5, "TRADE_RETCODE_PRICE_CHANGED", 10020): "price_changed",
        getattr(mt5, "TRADE_RETCODE_TIMEOUT", 10012): "timeout",
        getattr(mt5, "TRADE_RETCODE_INVALID_FILL", 10030): "filling_mode_error",
    }
    return mapping.get(retcode, "order_check_rejected" if check else "unknown_result")


def _sanitize_result(value: object) -> dict[str, object]:
    mapping = _as_mapping(value)
    allowed = {
        "retcode", "deal", "order", "volume", "price", "bid", "ask", "comment",
        "request_id", "retcode_external",
    }
    return redact_for_audit({key: mapping.get(key) for key in allowed if key in mapping})


def _sanitize_request(request: dict[str, object]) -> dict[str, object]:
    return redact_for_audit(dict(request))


def _sanitize_position(value: object) -> dict[str, object]:
    mapping = _as_mapping(value)
    allowed = {"ticket", "identifier", "symbol", "type", "volume", "price_open", "price_current", "sl", "tp", "profit", "time"}
    return {key: mapping.get(key) for key in allowed if key in mapping}


def _sanitize_order(value: object) -> dict[str, object]:
    mapping = _as_mapping(value)
    allowed = {"ticket", "order", "symbol", "type", "volume_initial", "volume_current", "price_open", "sl", "tp", "state", "time_setup"}
    return {key: mapping.get(key) for key in allowed if key in mapping}


def _last_error(mt5: Any) -> dict[str, object]:
    value = mt5.last_error()
    if isinstance(value, tuple) and len(value) >= 2:
        return {"code": value[0], "description": str(value[1])}
    return {"code": None, "description": "unavailable"}


def _as_mapping(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    converter = getattr(value, "_asdict", None)
    if callable(converter):
        converted = converter()
        return converted if isinstance(converted, dict) else {}
    return {}


def _hard_block(reasons: list[str]) -> dict[str, object]:
    return {
        **_blocked("account_identity_hard_block", reason_codes=reasons),
        "status": "HARD_BLOCK",
    }


def _blocked(
    reason: str,
    *,
    reason_codes: list[str] | None = None,
    last_error: dict[str, object] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "status": "BLOCKED",
        "reason": reason,
        "reason_codes": reason_codes or [reason],
        "order_send_allowed": False,
        "retry_allowed": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }
    if last_error is not None:
        result["last_error"] = redact_for_audit(last_error)
    return result

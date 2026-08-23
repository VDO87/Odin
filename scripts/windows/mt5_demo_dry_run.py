"""Windows MT5 Stage 0: live DEMO validation through order_check only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, os.environ["ODIN_RC1_REPO_SRC"])

import MetaTrader5 as mt5  # type: ignore[import-not-found]  # noqa: E402

from odin.contracts.demo_execution import DemoAccountEvidence, TradeProposal  # noqa: E402
from odin.risk.demo_execution import evaluate_demo_risk  # noqa: E402
from odin.trading.demo_execution_service import run_demo_dry_run  # noqa: E402
from odin.trading.demo_reconciliation import recovery_gate  # noqa: E402
from odin.trading.market_time import assess_market_timestamp  # noqa: E402


EXPECTED_BROKER = "OANDA TMS Brokers S.A."
SYMBOL = "EURUSD"


def main() -> int:
    terminal_path = os.environ["ODIN_RC1_TERMINAL_PATH"]
    connected = mt5.initialize(terminal_path, timeout=120_000)
    try:
        if not connected:
            code, description = mt5.last_error()
            return _finish(_blocked("initialize_failed", last_error={"code": code, "description": description}))
        control = _load_control(Path(os.environ["ODIN_RC1_CONTROL_PATH"]))
        if control is None:
            return _finish(_blocked("demo_execution_control_invalid"))
        account = _mapping(mt5.account_info())
        terminal = _mapping(mt5.terminal_info())
        symbol = _mapping(mt5.symbol_info(SYMBOL))
        tick = _mapping(mt5.symbol_info_tick(SYMBOL))
        if not all((account, terminal, symbol, tick)):
            return _finish(_blocked("mt5_preflight_evidence_missing"))
        expected_login = os.environ["ODIN_RC1_EXPECTED_LOGIN"]
        expected_server = os.environ["ODIN_RC1_EXPECTED_SERVER"]
        expected_terminal_info_path = str(Path(terminal_path).parent)
        identity_reasons = _identity_blocks(
            account=account,
            terminal=terminal,
            expected_terminal_info_path=expected_terminal_info_path,
            expected_login=expected_login,
            expected_server=expected_server,
        )
        if identity_reasons:
            return _finish(
                _blocked(
                    "account_identity_hard_block",
                    status="HARD_BLOCK",
                    reason_codes=identity_reasons,
                    public_evidence={
                        "observed_broker": account.get("company"),
                        "observed_server": account.get("server"),
                        "expected_server": expected_server,
                        "observed_terminal_path": terminal.get("path"),
                        "expected_terminal_path": expected_terminal_info_path,
                    },
                )
            )
        positions_value = mt5.positions_get()
        orders_value = mt5.orders_get()
        if positions_value is None or orders_value is None:
            return _finish(_blocked("broker_execution_snapshot_unavailable"))
        positions = [_mapping(item) for item in positions_value]
        orders = [_mapping(item) for item in orders_value]
        ledger_path = Path(os.environ["ODIN_RC1_LEDGER_PATH"])
        recovery = recovery_gate(
            ledger_path=ledger_path,
            broker_positions=positions,
            broker_orders=orders,
            terminal_connected=terminal.get("connected") is True,
        )
        proposal = _proposal(symbol, tick, control)
        evidence = _evidence(
            account=account,
            terminal=terminal,
            symbol=symbol,
            tick=tick,
            positions=positions,
            orders=orders,
            recovery=recovery,
            expected_terminal_info_path=expected_terminal_info_path,
            expected_login=expected_login,
            expected_server=expected_server,
            control=control,
        )
        risk = evaluate_demo_risk(proposal, evidence)
        result = run_demo_dry_run(
            mt5,
            proposal=proposal,
            evidence=evidence,
            risk_result=risk,
            ledger_path=ledger_path,
        )
        return _finish(_public_result(result, proposal, evidence, risk, account, terminal))
    finally:
        mt5.shutdown()


def _load_control(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    required = {
        "mode": "DEMO_EXECUTION_RC1",
        "allowed_symbol": SYMBOL,
        "kill_switch_engaged": False,
        "canary_authorized": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }
    return value if all(value.get(key) == expected for key, expected in required.items()) else None


def _identity_blocks(
    *,
    account: dict[str, object],
    terminal: dict[str, object],
    expected_terminal_info_path: str,
    expected_login: str,
    expected_server: str,
) -> list[str]:
    reasons: list[str] = []
    checks = (
        (account.get("trade_mode") != mt5.ACCOUNT_TRADE_MODE_DEMO, "account_not_demo"),
        (account.get("company") != EXPECTED_BROKER, "broker_mismatch"),
        (account.get("server") != expected_server, "server_mismatch"),
        (str(account.get("login", "")) != expected_login, "login_mismatch"),
        (
            str(terminal.get("path", "")).casefold() != expected_terminal_info_path.casefold(),
            "terminal_path_mismatch",
        ),
        (terminal.get("connected") is not True, "terminal_disconnected"),
    )
    reasons.extend(reason for failed, reason in checks if failed)
    return reasons


def _proposal(
    symbol: dict[str, object], tick: dict[str, object], control: dict[str, object]
) -> TradeProposal:
    now = datetime.now(UTC)
    point = _number(symbol.get("point"))
    digits = _integer(symbol.get("digits"))
    entry = round(_number(tick.get("ask")), digits)
    distance_points = max(_integer(symbol.get("trade_stops_level")) + 10, 100)
    stop_loss = round(entry - distance_points * point, digits)
    take_profit = round(entry + distance_points * point * 2, digits)
    market_payload = {
        "symbol": SYMBOL,
        "bid": tick.get("bid"),
        "ask": tick.get("ask"),
        "time": tick.get("time"),
    }
    market_hash = hashlib.sha256(
        json.dumps(market_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    proposal_id = "rc1-stage0-" + hashlib.sha256(
        f"{market_hash}|{now.isoformat()}".encode()
    ).hexdigest()[:20]
    return TradeProposal(
        proposal_id=proposal_id,
        decision_id="rc1-stage0-technical-dry-run",
        timestamp_utc=now.isoformat(),
        symbol=SYMBOL,
        side="BUY",
        volume=_number(control.get("fixed_volume")),
        entry_reference=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        strategy_id="rc1_stage0_fixed_minimum_volume",
        strategy_version="1",
        reason_codes=("technical_stage0_order_check_only",),
        market_data_hash=market_hash,
        data_quality="VALID",
        freshness="FRESH",
        expiry=(now.replace(microsecond=0) + timedelta(minutes=2)).isoformat(),
    )


def _evidence(
    *,
    account: dict[str, object],
    terminal: dict[str, object],
    symbol: dict[str, object],
    tick: dict[str, object],
    positions: list[dict[str, object]],
    orders: list[dict[str, object]],
    recovery: dict[str, object],
    expected_terminal_info_path: str,
    expected_login: str,
    expected_server: str,
    control: dict[str, object],
) -> DemoAccountEvidence:
    now = datetime.now(UTC)
    tick_time = tick.get("time")
    market_time = assess_market_timestamp(
        tick_time,
        now_utc=now,
        broker=str(account.get("company", "")),
        server=str(account.get("server", "")),
    )
    age = int(market_time.age_seconds) if market_time.age_seconds == market_time.age_seconds else -1
    balance = _number(account.get("balance"))
    equity = _number(account.get("equity"))
    drawdown = max(0.0, (balance - equity) / balance * 100) if balance > 0 else 100.0
    bid = _number(tick.get("bid"))
    ask = _number(tick.get("ask"))
    trade_mode = symbol.get("trade_mode")
    disabled = getattr(mt5, "SYMBOL_TRADE_MODE_DISABLED", 0)
    return DemoAccountEvidence(
        expected_terminal_path=expected_terminal_info_path,
        terminal_path=str(terminal.get("path", "")),
        expected_broker=EXPECTED_BROKER,
        broker=str(account.get("company", "")),
        expected_server=expected_server,
        server=str(account.get("server", "")),
        expected_login=expected_login,
        login=str(account.get("login", "")),
        account_mode="DEMO",
        terminal_connected=terminal.get("connected") is True,
        terminal_trade_allowed=(
            terminal.get("trade_allowed") is True
            and terminal.get("tradeapi_disabled") is not True
            and account.get("trade_allowed") is True
        ),
        market_open=trade_mode != disabled and bid > 0 and ask > bid,
        symbol=SYMBOL,
        data_fresh=market_time.status == "FRESH",
        data_age_seconds=age,
        reconciliation_status=str(recovery.get("status", "RECONCILIATION_BLOCK")),
        kill_switch_engaged=control.get("kill_switch_engaged") is True,
        open_positions=len(positions),
        active_orders=len(orders),
        free_margin=_number(account.get("margin_free")),
        daily_realized_pnl=_daily_realized_pnl(),
        drawdown_percent=drawdown,
        spread=ask - bid,
        volume_min=_number(symbol.get("volume_min")),
        volume_max=_number(symbol.get("volume_max")),
        volume_step=_number(symbol.get("volume_step")),
        point=_number(symbol.get("point")),
        digits=_integer(symbol.get("digits")),
        stops_level_points=_integer(symbol.get("trade_stops_level")),
        trade_tick_size=_number(symbol.get("trade_tick_size")),
        trade_tick_value_loss=_number(symbol.get("trade_tick_value_loss")),
        fallback_used=False,
        market_time_status=market_time.status,
        market_time_reason_codes=market_time.reason_codes,
        mt5_tick_time_raw=market_time.tick_time_raw,
        mt5_tick_time_msc_raw=_integer(tick.get("time_msc")) or None,
        mt5_tick_time_utc=market_time.tick_time_utc,
        odin_now_raw=market_time.now_raw,
        odin_now_utc=market_time.now_utc,
        broker_server_time=market_time.broker_server_time,
        normalized_event_time_utc=market_time.normalized_event_time_utc,
        normalization_method=market_time.normalization_method,
        observed_server_offset_seconds=market_time.observed_server_offset_seconds,
        normalization_confidence=market_time.normalization_confidence,
        market_time_source_profile=market_time.source_profile,
    )


def _daily_realized_pnl() -> float:
    now = datetime.now(UTC)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(start, now)
    if deals is None:
        return -50.0
    total = 0.0
    for deal in deals:
        value = _mapping(deal)
        total += sum(_number(value.get(key)) for key in ("profit", "commission", "swap", "fee"))
    return round(total, 2)


def _public_result(
    result: dict[str, object],
    proposal: TradeProposal,
    evidence: DemoAccountEvidence,
    risk: dict[str, object],
    account: dict[str, object],
    terminal: dict[str, object],
) -> dict[str, object]:
    service_evidence = _mapping(result.get("evidence"))
    return {
        "status": result.get("status", "BLOCKED"),
        "reason": result.get("reason"),
        "service_evidence": {
            "status": service_evidence.get("status"),
            "reason": service_evidence.get("reason"),
            "reason_codes": service_evidence.get("reason_codes", []),
        },
        "account": "DEMO",
        "broker": evidence.broker,
        "server": evidence.server,
        "terminal_path": terminal.get("path"),
        "terminal_connected": evidence.terminal_connected,
        "balance": account.get("balance"),
        "equity": account.get("equity"),
        "symbol": proposal.symbol,
        "volume": proposal.volume,
        "sl": proposal.stop_loss,
        "tp": proposal.take_profit,
        "max_loss_estimated": risk.get("estimated_max_loss"),
        "risk_status": risk.get("status"),
        "risk_reason_codes": risk.get("reason_codes"),
        "data_freshness": evidence.market_time_status,
        "data_age_seconds": evidence.data_age_seconds,
        "mt5_tick_time_raw": evidence.mt5_tick_time_raw,
        "mt5_tick_time_msc_raw": evidence.mt5_tick_time_msc_raw,
        "mt5_tick_time_utc": evidence.mt5_tick_time_utc,
        "odin_now_raw": evidence.odin_now_raw,
        "odin_now_utc": evidence.odin_now_utc,
        "calculated_age_seconds": evidence.data_age_seconds,
        "market_time_reason_codes": list(evidence.market_time_reason_codes),
        "broker_timestamp_raw": evidence.mt5_tick_time_raw,
        "broker_server_time": evidence.broker_server_time,
        "normalized_event_time_utc": evidence.normalized_event_time_utc,
        "normalization_method": evidence.normalization_method,
        "observed_server_offset_seconds": evidence.observed_server_offset_seconds,
        "normalization_confidence": evidence.normalization_confidence,
        "market_time_source_profile": evidence.market_time_source_profile,
        "timezone_assumptions": {
            "mt5_tick_time": "raw broker/server wall-clock epoch preserved for audit",
            "odin_now": "timezone-aware UTC",
            "allowed_future_clock_skew_seconds": 2,
            "normalization": "exact broker/server profile only; unknown or unexpected offset blocks",
        },
        "reconciliation": evidence.reconciliation_status,
        "order_check": _mapping(_mapping(result.get("order_check")).get("order_check_result")),
        "proposal_id": proposal.proposal_id,
        "canary_confirmation_required": True,
        "demo_execution": "ready" if result.get("status") == "DRY_RUN_VALIDATED" else "blocked",
        "broker_submission_called": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }


def _finish(result: dict[str, object]) -> int:
    destination = Path(os.environ["ODIN_RC1_REPORT_PATH"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "DRY_RUN_VALIDATED" else 1


def _blocked(
    reason: str,
    *,
    status: str = "BLOCKED",
    last_error: dict[str, object] | None = None,
    reason_codes: list[str] | None = None,
    public_evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "status": status,
        "reason": reason,
        "broker_submission_called": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }
    if last_error is not None:
        result["last_error"] = last_error
    if reason_codes is not None:
        result["reason_codes"] = reason_codes
    if public_evidence is not None:
        result["public_evidence"] = public_evidence
    return result


def _mapping(value: Any) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    converter = getattr(value, "_asdict", None)
    converted = converter() if callable(converter) else None
    return converted if isinstance(converted, dict) else {}


def _number(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _integer(value: object) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Persistent Windows supervisor for ODIN Autonomous DEMO Operations RC2.

This runtime starts in observation/reconciliation mode.  Financial submission
is only considered by the dedicated RC2 cycle after every gate is revalidated;
this supervisor module itself contains no direct ``order_send`` call.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import ctypes
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any
from urllib.request import urlopen


sys.path.insert(0, os.environ["ODIN_RC2_REPO_SRC"])
sys.path.insert(0, os.environ["ODIN_RC2_WINDOWS_SCRIPTS"])
os.environ.setdefault("ODIN_RC1_REPO_SRC", os.environ["ODIN_RC2_REPO_SRC"])

import MetaTrader5 as mt5  # type: ignore[import-not-found]  # noqa: E402

import mt5_demo_dry_run as stage0  # noqa: E402
from odin.contracts.demo_execution import TradeProposal  # noqa: E402
from odin.trading.autonomous_demo_state import (  # noqa: E402
    append_incident,
    build_supervisor_state,
    read_control,
    write_heartbeat,
    write_state,
)
from odin.trading.autonomous_demo_cycle import (  # noqa: E402
    build_market_bars,
    build_trade_candidate,
    load_autonomous_demo_policy,
    summarize_daily_deals,
)
from odin.trading.demo_decision_ledger import (  # noqa: E402
    append_demo_decision,
    demo_decision_already_recorded,
)
from odin.risk.demo_execution import evaluate_demo_risk  # noqa: E402
from odin.reporting.autonomous_demo_reports import (  # noqa: E402
    update_autonomous_demo_reports,
)
from odin.trading.demo_execution_service import run_autonomous_demo_order  # noqa: E402
from odin.trading.demo_position_lifecycle import (  # noqa: E402
    reconcile_latest_broker_close,
)
from odin.trading.demo_reconciliation import recovery_gate  # noqa: E402
from odin.trading.execution_ledger import completed_reconciled_lifecycle  # noqa: E402


EXPECTED_BROKER = "OANDA TMS Brokers S.A."
EXPECTED_SERVER = "OANDATMS-MT5"
CANONICAL_SYMBOL = "EURUSD"
BROKER_SYMBOL = "EURUSD.pro"
AUTHORIZED_TERMINAL = r"C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe"
EXCLUDED_TERMINAL = r"D:\ODIN_LOCAL\mt5\terminal64.exe"
MUTEX_NAME = "Local\\ODIN_AUTONOMOUS_DEMO_RC2_SUPERVISOR"
ERROR_ALREADY_EXISTS = 183
STOP_REQUESTED = False


def main() -> int:
    mutex = _acquire_single_instance()
    if mutex is None:
        print(json.dumps(_public_event("DUPLICATE_SUPERVISOR_BLOCKED")), flush=True)
        return 0
    _install_signal_handlers()
    started = datetime.now(UTC)
    cycle = 0
    failure_count = 0
    interval = _bounded_integer(os.environ.get("ODIN_RC2_CYCLE_SECONDS"), 30, 5, 300)
    state_path = Path(os.environ["ODIN_RC2_STATE_PATH"])
    heartbeat_path = Path(os.environ["ODIN_RC2_HEARTBEAT_PATH"])
    incidents_path = Path(os.environ["ODIN_RC2_INCIDENTS_PATH"])
    control_path = Path(os.environ["ODIN_RC2_CONTROL_PATH"])
    try:
        while not STOP_REQUESTED:
            cycle += 1
            control = read_control(control_path)
            try:
                observation = _observe_once()
                control = read_control(control_path)
                state, reasons = _classify_state(observation, control)
                if state == "READY_FOR_DECISION":
                    autonomous = _run_autonomous_demo_cycle(control)
                    state = str(autonomous["state"])
                    reasons = [str(item) for item in autonomous["reason_codes"]]
                    details = autonomous.get("observed")
                    if isinstance(details, dict):
                        observation.update(details)
                failure_count = 0 if state not in {"DEGRADED", "RECOVERING"} else failure_count + 1
            except Exception as error:  # fail closed, persist, and continue
                failure_count += 1
                state = "RECOVERING" if failure_count <= 3 else "DEGRADED"
                reasons = ["supervisor_cycle_exception"]
                observation = {
                    "terminal_path": AUTHORIZED_TERMINAL,
                    "error_type": type(error).__name__,
                    "broker_submission_called": False,
                }
                append_incident(
                    incidents_path,
                    incident_type="SUPERVISOR_CYCLE_EXCEPTION",
                    component="mt5_autonomous_demo_supervisor",
                    error_code=type(error).__name__,
                    root_cause="runtime_cycle_failed",
                    evidence=observation,
                )
            snapshot = build_supervisor_state(
                state,
                cycle=cycle,
                reason_codes=reasons,
                observed=observation,
                branch=os.environ.get("ODIN_RC2_BRANCH", ""),
                checkpoint=os.environ.get("ODIN_RC2_CHECKPOINT", ""),
            )
            write_state(state_path, snapshot)
            try:
                update_autonomous_demo_reports(
                    report_root=os.environ["ODIN_RC2_REPORT_ROOT"],
                    supervisor_state=snapshot,
                    ledger_path=os.environ["ODIN_RC2_LEDGER_PATH"],
                    decision_ledger_path=os.environ["ODIN_RC2_DECISION_LEDGER_PATH"],
                    incidents_path=incidents_path,
                    hermes_claims_path=os.environ.get("ODIN_RC2_HERMES_CLAIMS_PATH"),
                )
            except Exception as error:  # reporting is non-authoritative and fail-visible
                append_incident(
                    incidents_path,
                    incident_type="AUTONOMOUS_REPORTING_EXCEPTION",
                    component="autonomous_demo_reports",
                    error_code=type(error).__name__,
                    root_cause="runtime_reporting_failed",
                    evidence={"error_type": type(error).__name__},
                    checkpoint=os.environ.get("ODIN_RC2_CHECKPOINT", ""),
                )
            delay = min(300, interval * (2 ** min(failure_count, 3)))
            next_check = datetime.now(UTC) + timedelta(seconds=delay)
            write_heartbeat(
                heartbeat_path,
                cycle=cycle,
                state=state,
                process_id=os.getpid(),
                started_at_utc=started.isoformat(),
                next_check_at_utc=next_check.isoformat(),
            )
            print(
                json.dumps(
                    _public_event(
                        state,
                        reasons,
                        cycle=cycle,
                        broker_submission_called=observation.get("broker_submission_called")
                        is True,
                    )
                ),
                flush=True,
            )
            _sleep_bounded(
                delay,
                control_path=control_path,
                previous_request_id=str(control.get("request_id", "")),
            )
    finally:
        ctypes.windll.kernel32.CloseHandle(mutex)
    return 0


def _observe_once() -> dict[str, object]:
    dashboard_status = _ensure_dashboard()
    terminal_path = os.environ["ODIN_RC2_TERMINAL_PATH"]
    if terminal_path.casefold() != AUTHORIZED_TERMINAL.casefold():
        return _hard_block_observation("terminal_path_not_allowlisted", terminal_path)
    if terminal_path.casefold() == EXCLUDED_TERMINAL.casefold():
        return _hard_block_observation("metaquotes_demo_terminal_forbidden", terminal_path)
    connected = mt5.initialize(terminal_path, timeout=120_000)
    try:
        if not connected:
            code, description = mt5.last_error()
            return {
                "status": "RECOVERING",
                "reason_codes": ["mt5_initialize_failed"],
                "last_error": {"code": code, "description": str(description)},
                "terminal_path": terminal_path,
                "broker_submission_called": False,
                "dashboard": dashboard_status,
            }
        account = stage0._mapping(mt5.account_info())
        terminal = stage0._mapping(mt5.terminal_info())
        symbol = stage0._mapping(mt5.symbol_info(BROKER_SYMBOL))
        tick = stage0._mapping(mt5.symbol_info_tick(BROKER_SYMBOL))
        if not all((account, terminal, symbol, tick)):
            return _hard_block_observation("mt5_identity_or_market_evidence_missing", terminal_path)
        expected_login = os.environ["ODIN_RC2_EXPECTED_LOGIN"]
        expected_terminal_info_path = str(Path(terminal_path).parent)
        identity_reasons = stage0._identity_blocks(
            account=account,
            terminal=terminal,
            expected_terminal_info_path=expected_terminal_info_path,
            expected_login=expected_login,
            expected_server=EXPECTED_SERVER,
        )
        if account.get("company") != EXPECTED_BROKER:
            identity_reasons.append("broker_mismatch")
        if str(symbol.get("name", "")) != BROKER_SYMBOL:
            identity_reasons.append("broker_symbol_mismatch")
        if identity_reasons:
            return {
                "status": "SECURITY_HARD_BLOCK",
                "reason_codes": sorted(set(identity_reasons)),
                "broker": account.get("company"),
                "server": account.get("server"),
                "terminal_path": terminal.get("path"),
                "logical_symbol": CANONICAL_SYMBOL,
                "broker_symbol": symbol.get("name"),
                "broker_submission_called": False,
                "dashboard": dashboard_status,
            }
        positions_value = mt5.positions_get()
        orders_value = mt5.orders_get()
        if positions_value is None or orders_value is None:
            return {
                "status": "DEGRADED",
                "reason_codes": ["broker_execution_snapshot_unavailable"],
                "broker_submission_called": False,
                "dashboard": dashboard_status,
            }
        positions = [stage0._mapping(item) for item in positions_value]
        orders = [stage0._mapping(item) for item in orders_value]
        ledger_path = Path(os.environ["ODIN_RC2_LEDGER_PATH"])
        lifecycle = reconcile_latest_broker_close(
            mt5,
            ledger_path=ledger_path,
            broker_positions=positions,
            broker_orders=orders,
            broker=str(account.get("company", "")),
            server=str(account.get("server", "")),
            point=stage0._number(symbol.get("point")),
        )
        recovery = recovery_gate(
            ledger_path=ledger_path,
            broker_positions=positions,
            broker_orders=orders,
            terminal_connected=terminal.get("connected") is True,
        )
        control = {"kill_switch_engaged": False, "fixed_volume": 0.01}
        evidence = stage0._evidence(
            account=account,
            terminal=terminal,
            symbol=symbol,
            tick=tick,
            positions=positions,
            orders=orders,
            recovery=recovery,
            expected_terminal_info_path=expected_terminal_info_path,
            expected_login=expected_login,
            expected_server=EXPECTED_SERVER,
            control=control,
        )
        daily = _daily_trade_summary()
        evidence = replace(
            evidence,
            daily_realized_pnl=float(daily["daily_realized_pnl"]),
            completed_trades_today=int(daily["completed_trades_today"]),
        )
        candles = _recent_candles()
        _persist_readonly_snapshot(account, tick, evidence, positions, candles)
        return {
            "status": "OK",
            "account_mode": "DEMO",
            "broker": evidence.broker,
            "server": evidence.server,
            "terminal_path": terminal_path,
            "terminal_connected": evidence.terminal_connected,
            "terminal_trade_allowed": evidence.terminal_trade_allowed,
            "account_trade_allowed": account.get("trade_allowed") is True,
            "account_trade_expert": account.get("trade_expert") is True,
            "terminal_tradeapi_disabled": terminal.get("tradeapi_disabled") is True,
            "logical_symbol": CANONICAL_SYMBOL,
            "broker_symbol": evidence.broker_symbol,
            "market_open": evidence.market_open,
            "data_freshness": evidence.market_time_status,
            "data_age_seconds": evidence.data_age_seconds,
            "normalized_event_time_utc": evidence.normalized_event_time_utc,
            "broker_timestamp_raw": evidence.mt5_tick_time_raw,
            "time_profile": evidence.market_time_source_profile,
            "spread": evidence.spread,
            "spread_points": round(evidence.spread / evidence.point, 2)
            if evidence.point > 0
            else None,
            "positions_count": len(positions),
            "orders_count": len(orders),
            "reconciliation": recovery.get("status"),
            "position_lifecycle": lifecycle.get("status"),
            "latest_close_reason": lifecycle.get("close_reason"),
            "latest_closed_realized_pnl": lifecycle.get("realized_pnl"),
            "daily_history_status": daily.get("status"),
            "daily_realized_pnl": evidence.daily_realized_pnl,
            "completed_trades_today": evidence.completed_trades_today,
            "bid": tick.get("bid"),
            "ask": tick.get("ask"),
            "point": symbol.get("point"),
            "digits": symbol.get("digits"),
            "symbol_trade_mode": symbol.get("trade_mode"),
            "balance": account.get("balance"),
            "equity": account.get("equity"),
            "margin": account.get("margin"),
            "free_margin": account.get("margin_free"),
            "broker_submission_called": False,
            "dashboard": dashboard_status,
        }
    finally:
        mt5.shutdown()


def _classify_state(
    observation: dict[str, object], control: dict[str, object]
) -> tuple[str, list[str]]:
    observed_status = str(observation.get("status", "DEGRADED"))
    reasons = [str(item) for item in observation.get("reason_codes", [])]
    if observed_status == "SECURITY_HARD_BLOCK":
        return "SECURITY_HARD_BLOCK", reasons or ["identity_hard_block"]
    if observed_status == "RECOVERING":
        return "RECOVERING", reasons or ["mt5_reconnecting"]
    if observed_status != "OK":
        return "DEGRADED", reasons or ["observation_degraded"]
    action = control.get("action")
    if action in {"PAUSE", "SAFE_STOP"}:
        return "EXECUTION_PAUSED", [f"operator_{str(action).lower()}"]
    if observation.get("reconciliation") != "RECONCILED":
        return "RECONCILING", ["broker_ledger_reconciliation_required"]
    positions = int(observation.get("positions_count", 0))
    if positions > 0:
        return "POSITION_MONITOR", ["broker_position_open"]
    if observation.get("data_freshness") != "FRESH" or observation.get("market_open") is not True:
        return "WAITING_MARKET", ["market_closed_or_stale"]
    if observation.get("terminal_trade_allowed") is not True:
        return "EXECUTION_PAUSED", ["terminal_trading_not_allowed"]
    if observation.get("daily_history_status") != "OK":
        return "EXECUTION_PAUSED", ["daily_broker_history_unavailable"]
    if action != "RESUME":
        return "MONITOR_ONLY", ["operator_resume_required"]
    return "READY_FOR_DECISION", ["all_runtime_preconditions_revalidated"]


def _run_autonomous_demo_cycle(control: dict[str, object]) -> dict[str, object]:
    """Revalidate all evidence and delegate at most one proposal to the service."""
    if control.get("action") != "RESUME":
        return _cycle_result("EXECUTION_PAUSED", ["operator_resume_required"])
    try:
        policy = load_autonomous_demo_policy(os.environ["ODIN_RC2_CONFIG_PATH"])
    except (KeyError, ValueError) as error:
        return _cycle_result("SECURITY_HARD_BLOCK", [str(error)])
    if not completed_reconciled_lifecycle(
        os.environ["ODIN_RC2_LEDGER_PATH"], policy.required_canary_decision_id
    ):
        return _cycle_result("EXECUTION_PAUSED", ["initial_canary_not_reconciled"])
    connected = mt5.initialize(policy.terminal_path, timeout=120_000)
    try:
        if not connected:
            return _cycle_result("RECOVERING", ["mt5_revalidation_failed"])
        account = stage0._mapping(mt5.account_info())
        terminal = stage0._mapping(mt5.terminal_info())
        symbol = stage0._mapping(mt5.symbol_info(policy.broker_symbol))
        tick = stage0._mapping(mt5.symbol_info_tick(policy.broker_symbol))
        if not all((account, terminal, symbol, tick)):
            return _cycle_result("SECURITY_HARD_BLOCK", ["execution_preflight_evidence_missing"])
        expected_login = os.environ["ODIN_RC2_EXPECTED_LOGIN"]
        expected_terminal_info_path = str(Path(policy.terminal_path).parent)
        identity_reasons = stage0._identity_blocks(
            account=account,
            terminal=terminal,
            expected_terminal_info_path=expected_terminal_info_path,
            expected_login=expected_login,
            expected_server=policy.server,
        )
        if account.get("company") != policy.broker:
            identity_reasons.append("broker_mismatch")
        if str(symbol.get("name", "")) != policy.broker_symbol:
            identity_reasons.append("broker_symbol_mismatch")
        if identity_reasons:
            return _cycle_result("SECURITY_HARD_BLOCK", sorted(set(identity_reasons)))
        positions_value = mt5.positions_get()
        orders_value = mt5.orders_get()
        if positions_value is None or orders_value is None:
            return _cycle_result("DEGRADED", ["broker_execution_snapshot_unavailable"])
        positions = [stage0._mapping(item) for item in positions_value]
        orders = [stage0._mapping(item) for item in orders_value]
        recovery = recovery_gate(
            ledger_path=os.environ["ODIN_RC2_LEDGER_PATH"],
            broker_positions=positions,
            broker_orders=orders,
            terminal_connected=terminal.get("connected") is True,
        )
        evidence = stage0._evidence(
            account=account,
            terminal=terminal,
            symbol=symbol,
            tick=tick,
            positions=positions,
            orders=orders,
            recovery=recovery,
            expected_terminal_info_path=expected_terminal_info_path,
            expected_login=expected_login,
            expected_server=policy.server,
            control={"kill_switch_engaged": False, "fixed_volume": policy.fixed_volume},
        )
        daily = _daily_trade_summary()
        evidence = replace(
            evidence,
            daily_realized_pnl=float(daily["daily_realized_pnl"]),
            completed_trades_today=int(daily["completed_trades_today"]),
        )
        if daily["status"] != "OK":
            return _cycle_result(
                "EXECUTION_PAUSED",
                ["daily_broker_history_unavailable"],
                evidence=evidence,
            )
        rates = _recent_candles()
        bars_result = build_market_bars(
            rates,
            broker=policy.broker,
            server=policy.server,
            logical_symbol=policy.logical_symbol,
            point=evidence.point,
            now_utc=datetime.now(UTC),
        )
        bars = bars_result.get("bars")
        if bars_result.get("status") != "VALIDATED" or not isinstance(bars, list):
            return _cycle_result(
                "DEGRADED",
                [str(bars_result.get("reason", "market_bars_blocked"))],
                evidence=evidence,
            )
        candidate = build_trade_candidate(
            bars,
            tick=tick,
            symbol=symbol,
            policy=policy,
            now_utc=datetime.now(UTC),
        )
        decision = candidate.get("decision")
        if not isinstance(decision, dict):
            return _cycle_result(
                "NO_TRADE",
                [str(candidate.get("reason", "decision_unavailable"))],
                evidence=evidence,
            )
        decision_id = str(decision.get("decision_id", ""))
        decision_path = os.environ["ODIN_RC2_DECISION_LEDGER_PATH"]
        if demo_decision_already_recorded(decision_path, decision_id):
            return _cycle_result(
                "NO_TRADE",
                ["decision_already_processed"],
                evidence=evidence,
                decision=decision,
            )
        proposal = candidate.get("proposal")
        risk: dict[str, object] | None = None
        if candidate.get("status") == "PROPOSAL_CREATED":
            if not isinstance(proposal, TradeProposal):
                return _cycle_result(
                    "EXECUTION_PAUSED",
                    ["trade_proposal_contract_invalid"],
                    evidence=evidence,
                    decision=decision,
                )
            risk = evaluate_demo_risk(proposal, evidence, limits=policy.limits())
        recorded = _record_runtime_decision(
            decision_path=decision_path,
            decision=decision,
            proposal=proposal,
            evidence=evidence,
            risk=risk,
        )
        if recorded.get("status") != "RECORDED":
            return _cycle_result(
                "EXECUTION_PAUSED",
                ["demo_decision_ledger_blocked"],
                evidence=evidence,
                decision=decision,
                risk=risk,
            )
        if candidate.get("status") != "PROPOSAL_CREATED":
            return _cycle_result(
                "NO_TRADE",
                [str(item) for item in candidate.get("reason_codes", [])]
                or ["decision_not_actionable"],
                evidence=evidence,
                decision=decision,
            )
        if risk is None or risk.get("status") != "ALLOW_DEMO":
            reasons = risk.get("reason_codes", []) if isinstance(risk, dict) else []
            return _cycle_result(
                "EXECUTION_PAUSED" if "kill_switch_engaged" in reasons else "NO_TRADE",
                [str(item) for item in reasons] or ["risk_not_allow_demo"],
                evidence=evidence,
                decision=decision,
                risk=risk,
            )
        result = run_autonomous_demo_order(
            mt5,
            proposal=proposal,
            evidence=evidence,
            risk_result=risk,
            authorization=policy.authorization(evidence),
            ledger_path=os.environ["ODIN_RC2_LEDGER_PATH"],
            limits=policy.limits(),
            now_utc=datetime.now(UTC),
        )
        result_status = str(result.get("status", "BLOCKED"))
        submission_called = result.get("order_send_called") is True
        if result_status == "AUTONOMOUS_DEMO_SUBMITTED_AND_RECONCILED":
            state = "POSITION_OPEN"
            reasons = ["demo_position_submitted_and_reconciled"]
        elif result_status == "AUTONOMOUS_DEMO_REJECTED_RECONCILED":
            state = "NO_TRADE"
            reasons = ["broker_rejected_without_retry"]
        elif result_status == "RECONCILIATION_BLOCK":
            state = "RECONCILING"
            reasons = [str(result.get("reason", "post_submit_reconciliation_block"))]
        else:
            state = "EXECUTION_PAUSED"
            reasons = [str(result.get("reason", "execution_service_blocked"))]
        return _cycle_result(
            state,
            reasons,
            evidence=evidence,
            decision=decision,
            risk=risk,
            execution=result,
            broker_submission_called=submission_called,
        )
    finally:
        mt5.shutdown()


def _record_runtime_decision(
    *,
    decision_path: str,
    decision: dict[str, object],
    proposal: object,
    evidence: Any,
    risk: dict[str, object] | None,
) -> dict[str, object]:
    proposal_id = getattr(proposal, "proposal_id", None)
    if not isinstance(proposal_id, str):
        proposal_id = "no-proposal:" + str(decision.get("decision_id", ""))
    return append_demo_decision(
        path=decision_path,
        decision={
            **decision,
            "proposal_id": proposal_id,
            "decision_status": "AUTONOMOUS_DEMO_EVALUATED",
            "account_mode": "DEMO",
            "broker": evidence.broker,
            "server": evidence.server,
            "broker_symbol": evidence.broker_symbol,
            "risk_status": risk.get("status") if isinstance(risk, dict) else None,
            "risk_reason_codes": risk.get("reason_codes") if isinstance(risk, dict) else [],
            "execution_allowed": False,
            "safe_to_trade": False,
            "real_trading": False,
        },
    )


def _cycle_result(
    state: str,
    reasons: list[str],
    *,
    evidence: Any | None = None,
    decision: dict[str, object] | None = None,
    risk: dict[str, object] | None = None,
    execution: dict[str, object] | None = None,
    broker_submission_called: bool = False,
) -> dict[str, object]:
    observed: dict[str, object] = {
        "broker_submission_called": broker_submission_called,
        "latest_decision": _public_decision(decision),
        "risk": _public_status(risk),
        "execution": _public_status(execution),
    }
    if evidence is not None:
        observed.update(
            {
                "daily_realized_pnl": evidence.daily_realized_pnl,
                "completed_trades_today": evidence.completed_trades_today,
            }
        )
    return {"state": state, "reason_codes": reasons, "observed": observed}


def _public_decision(value: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {
        key: value.get(key)
        for key in (
            "decision_id",
            "timestamp",
            "symbol",
            "timeframe",
            "strategy_id",
            "signal",
            "confidence",
            "reason_codes",
            "data_quality",
            "freshness",
        )
    }


def _public_status(value: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {
        "status": value.get("status"),
        "reason": value.get("reason"),
        "reason_codes": value.get("reason_codes", []),
        "order_send_called": value.get("order_send_called", False),
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _daily_trade_summary() -> dict[str, object]:
    now = datetime.now(UTC)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    deals_value = mt5.history_deals_get(start, now)
    deals = [stage0._mapping(item) for item in deals_value] if deals_value is not None else None
    return summarize_daily_deals(
        deals,
        broker_symbol=BROKER_SYMBOL,
        exit_entries={
            getattr(mt5, "DEAL_ENTRY_OUT", 1),
            getattr(mt5, "DEAL_ENTRY_OUT_BY", 3),
        },
    )


def _ensure_dashboard() -> str:
    try:
        with urlopen("http://127.0.0.1:8765/health", timeout=3) as response:
            if response.status == 200:
                return "RUNNING"
    except OSError:
        pass
    launcher = os.environ.get("ODIN_RC2_DASHBOARD_LAUNCHER", "")
    if not launcher:
        return "DEGRADED"
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                launcher,
            ],
            check=False,
            timeout=30,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "RECOVERY_FAILED"
    return "RESTART_REQUESTED" if completed.returncode == 0 else "RECOVERY_FAILED"


def _recent_candles() -> list[dict[str, object]]:
    raw = mt5.copy_rates_from_pos(BROKER_SYMBOL, mt5.TIMEFRAME_M15, 0, 64)
    if raw is None:
        return []
    result: list[dict[str, object]] = []
    for item in raw:
        value = _rate_mapping(item)
        result.append(
            {
                "time": value.get("time"),
                "open": value.get("open"),
                "high": value.get("high"),
                "low": value.get("low"),
                "close": value.get("close"),
                "tick_volume": value.get("tick_volume"),
                "real_volume": value.get("real_volume"),
                "spread": value.get("spread"),
            }
        )
    return result


def _rate_mapping(value: object) -> dict[str, object]:
    mapping = stage0._mapping(value)
    if mapping:
        return mapping
    dtype = getattr(value, "dtype", None)
    names = getattr(dtype, "names", None)
    if not isinstance(names, tuple):
        return {}
    result: dict[str, object] = {}
    for name in names:
        item = value[name]  # type: ignore[index]
        scalar = getattr(item, "item", None)
        result[str(name)] = scalar() if callable(scalar) else item
    return result


def _persist_readonly_snapshot(
    account: dict[str, object],
    tick: dict[str, object],
    evidence: Any,
    positions: list[dict[str, object]],
    candles: list[dict[str, object]],
) -> None:
    now = datetime.now(UTC).isoformat()
    safe_positions = [
        {
            key: item.get(key)
            for key in (
                "ticket",
                "identifier",
                "symbol",
                "type",
                "volume",
                "price_open",
                "price_current",
                "sl",
                "tp",
                "profit",
                "time",
            )
        }
        for item in positions
    ]
    unsigned: dict[str, object] = {
        "status": "CONNECTED_DEMO_READ_ONLY",
        "as_of": now,
        "account": {
            "currency": account.get("currency"),
            "balance": account.get("balance"),
            "equity": account.get("equity"),
            "margin": account.get("margin"),
            "free_margin": account.get("margin_free"),
        },
        "positions": safe_positions,
        "market": {
            "symbol": CANONICAL_SYMBOL,
            "broker_symbol": BROKER_SYMBOL,
            "status": evidence.market_time_status,
            "bid": tick.get("bid"),
            "ask": tick.get("ask"),
            "as_of": evidence.normalized_event_time_utc,
            "candles": candles,
        },
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }
    unsigned["content_hash"] = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    target = Path(os.environ["ODIN_RC2_MT5_STATE_PATH"])
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(unsigned, sort_keys=True), encoding="utf-8")
    temporary.replace(target)


def _hard_block_observation(reason: str, terminal_path: str) -> dict[str, object]:
    return {
        "status": "SECURITY_HARD_BLOCK",
        "reason_codes": [reason],
        "terminal_path": terminal_path,
        "broker_submission_called": False,
    }


def _public_event(
    state: str,
    reason_codes: list[str] | None = None,
    *,
    cycle: int = 0,
    broker_submission_called: bool = False,
) -> dict[str, object]:
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "state": state,
        "cycle": cycle,
        "reason_codes": reason_codes or [],
        "broker_submission_called": broker_submission_called,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }


def _acquire_single_instance() -> int | None:
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle or ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
        return None
    return int(handle)


def _install_signal_handlers() -> None:
    def stop(_signum: int, _frame: object) -> None:
        global STOP_REQUESTED
        STOP_REQUESTED = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)


def _sleep_bounded(
    seconds: int,
    *,
    control_path: Path,
    previous_request_id: str,
) -> None:
    deadline = time.monotonic() + seconds
    while not STOP_REQUESTED and time.monotonic() < deadline:
        current = read_control(control_path)
        current_request_id = str(current.get("request_id", ""))
        if current_request_id and current_request_id != previous_request_id:
            return
        time.sleep(min(1.0, deadline - time.monotonic()))


def _bounded_integer(value: str | None, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        return default
    return min(maximum, max(minimum, parsed))


if __name__ == "__main__":
    raise SystemExit(main())

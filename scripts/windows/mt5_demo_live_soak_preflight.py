"""One read-only MT5 observation for the bounded DEMO soak controller."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.environ["ODIN_RC1_REPO_SRC"])

import MetaTrader5 as mt5  # type: ignore[import-not-found]  # noqa: E402

import mt5_demo_dry_run as stage0  # noqa: E402
from odin.contracts.demo_execution import DemoAccountEvidence, DemoRiskLimits  # noqa: E402
from odin.risk.demo_execution import evaluate_demo_risk  # noqa: E402
from odin.trading.demo_live_soak import (  # noqa: E402
    SoakCycleEvidence,
    SoakLimits,
    run_bounded_precanary_soak,
)
from odin.trading.demo_reconciliation import recovery_gate  # noqa: E402
from odin.trading.execution_ledger import submission_already_attempted  # noqa: E402


SYMBOL = "EURUSD"


def main() -> int:
    terminal_path = os.environ["ODIN_RC1_TERMINAL_PATH"]
    connected = mt5.initialize(terminal_path, timeout=120_000)
    try:
        if not connected:
            code, _ = mt5.last_error()
            return _finish(_blocked("initialize_failed", error_code=code))
        control = stage0._load_control(Path(os.environ["ODIN_RC1_CONTROL_PATH"]))
        if control is None:
            return _finish(_blocked("demo_execution_control_invalid"))
        account = stage0._mapping(mt5.account_info())
        terminal = stage0._mapping(mt5.terminal_info())
        symbol = stage0._mapping(mt5.symbol_info(SYMBOL))
        tick = stage0._mapping(mt5.symbol_info_tick(SYMBOL))
        if not all((account, terminal, symbol, tick)):
            return _finish(_blocked("mt5_preflight_evidence_missing"))
        positions_value = mt5.positions_get()
        orders_value = mt5.orders_get()
        if positions_value is None or orders_value is None:
            return _finish(_blocked("broker_execution_snapshot_unavailable"))
        positions = [stage0._mapping(item) for item in positions_value]
        orders = [stage0._mapping(item) for item in orders_value]
        ledger_path = Path(os.environ["ODIN_RC1_LEDGER_PATH"])
        recovery = recovery_gate(
            ledger_path=ledger_path,
            broker_positions=positions,
            broker_orders=orders,
            terminal_connected=terminal.get("connected") is True,
        )
        expected_terminal_info_path = str(Path(terminal_path).parent)
        proposal = stage0._proposal(symbol, tick, control)
        execution_evidence = stage0._evidence(
            account=account,
            terminal=terminal,
            symbol=symbol,
            tick=tick,
            positions=positions,
            orders=orders,
            recovery=recovery,
            expected_terminal_info_path=expected_terminal_info_path,
            expected_login=os.environ["ODIN_RC1_EXPECTED_LOGIN"],
            expected_server=os.environ["ODIN_RC1_EXPECTED_SERVER"],
            control=control,
        )
        risk = evaluate_demo_risk(proposal, execution_evidence)
        cycle = _cycle_evidence(
            account=account,
            symbol=symbol,
            positions=positions,
            orders=orders,
            proposal_id=proposal.proposal_id,
            execution_evidence=execution_evidence,
            risk=risk,
            control=control,
            ledger_path=ledger_path,
        )
        result = run_bounded_precanary_soak(
            observe=lambda _: cycle,
            report_dir=os.environ["ODIN_RC1_SOAK_REPORT_DIR"],
            limits=SoakLimits(max_cycles=1),
            git_checkpoint=os.environ.get("ODIN_RC1_GIT_CHECKPOINT", "UNKNOWN"),
        )
        return _finish(_public_result(result))
    finally:
        mt5.shutdown()


def _cycle_evidence(
    *,
    account: dict[str, object],
    symbol: dict[str, object],
    positions: list[dict[str, object]],
    orders: list[dict[str, object]],
    proposal_id: str,
    execution_evidence: DemoAccountEvidence,
    risk: dict[str, object],
    control: dict[str, object],
    ledger_path: Path,
) -> SoakCycleEvidence:
    limits = DemoRiskLimits()
    spread_price = float(execution_evidence.spread)
    point = float(execution_evidence.point)
    account_mode = _account_mode(account.get("trade_mode"))
    reasons = risk.get("reason_codes")
    reason_codes = tuple(str(reason) for reason in reasons) if isinstance(reasons, list) else ()
    return SoakCycleEvidence(
        observed_at_utc=datetime.now(UTC).isoformat(),
        account_mode=account_mode,
        broker=str(execution_evidence.broker),
        server=str(execution_evidence.server),
        terminal_path=str(execution_evidence.terminal_path),
        terminal_connected=bool(execution_evidence.terminal_connected),
        terminal_trade_allowed=bool(execution_evidence.terminal_trade_allowed),
        account_trade_allowed=account.get("trade_allowed") is True,
        account_trade_expert=account.get("trade_expert") is True,
        symbol=str(execution_evidence.symbol),
        trade_mode=stage0._integer(symbol.get("trade_mode")),
        data_fresh=bool(execution_evidence.data_fresh),
        time_normalization_valid=execution_evidence.market_time_status != "BLOCKED",
        normalized_event_time_utc=execution_evidence.normalized_event_time_utc,
        data_age_seconds=float(execution_evidence.data_age_seconds),
        spread_price=spread_price,
        spread_points=spread_price / point if point > 0 else -1.0,
        spread_limit_price=limits.max_spread,
        spread_limit_points=limits.max_spread / point if point > 0 else -1.0,
        reconciliation_status=str(execution_evidence.reconciliation_status),
        risk_status=str(risk.get("status", "BLOCK")),
        risk_reason_codes=reason_codes,
        kill_switch_engaged=control.get("kill_switch_engaged") is True,
        position_count=len(positions),
        position_reconciled=execution_evidence.reconciliation_status == "RECONCILED",
        pending_execution=bool(orders),
        proposal_duplicate=submission_already_attempted(ledger_path, proposal_id),
        proposal_available=True,
        no_trade=False,
        broker_submission_called=False,
        realized_pnl=float(execution_evidence.daily_realized_pnl),
        floating_pnl=sum(stage0._number(item.get("profit")) for item in positions),
        drawdown_demo_percent=float(execution_evidence.drawdown_percent),
        margin=stage0._number(account.get("margin")),
        free_margin=float(execution_evidence.free_margin),
        daily_loss=max(0.0, -float(execution_evidence.daily_realized_pnl)),
    )


def _account_mode(value: object) -> str:
    if value == mt5.ACCOUNT_TRADE_MODE_DEMO:
        return "DEMO"
    if value == mt5.ACCOUNT_TRADE_MODE_REAL:
        return "REAL"
    return "UNKNOWN"


def _public_result(result: dict[str, object]) -> dict[str, object]:
    decision = result.get("last_decision")
    metrics = result.get("metrics")
    return {
        "status": result.get("status", "STOPPED_PRE_CANARY"),
        "last_decision": decision if isinstance(decision, dict) else {},
        "metrics": metrics if isinstance(metrics, dict) else {},
        "broker_submission_called": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }


def _blocked(reason: str, *, error_code: object | None = None) -> dict[str, object]:
    return {
        "status": "STOPPED_PRE_CANARY",
        "reason": reason,
        "error_code": error_code,
        "broker_submission_called": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }


def _finish(result: dict[str, object]) -> int:
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "STAGE0_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())

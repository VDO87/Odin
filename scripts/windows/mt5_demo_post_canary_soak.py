"""Bounded read-only supervision of one confirmed MT5 DEMO CANARY."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.environ["ODIN_RC1_REPO_SRC"])

import MetaTrader5 as mt5  # type: ignore[import-not-found]  # noqa: E402

import mt5_demo_dry_run as stage0  # noqa: E402
from mt5_demo_live_soak_preflight import _cycle_evidence  # noqa: E402
from odin.risk.demo_execution import evaluate_demo_risk  # noqa: E402
from odin.trading.demo_live_soak import (  # noqa: E402
    SoakCycleEvidence,
    SoakLimits,
    run_bounded_postcanary_soak,
)
from odin.trading.demo_reconciliation import recovery_gate  # noqa: E402


BROKER_SYMBOL = "EURUSD.pro"


def main() -> int:
    canary = _load_json(Path(os.environ["ODIN_RC1_CANARY_REPORT_PATH"]))
    if (
        canary.get("status") != "CANARY_SUBMITTED_AND_RECONCILED"
        or canary.get("broker_submission_called") is not True
        or canary.get("real_trading") is not False
        or canary.get("execution_allowed") is not False
    ):
        return _finish(_blocked("validated_canary_report_required"))
    if not Path(os.environ["ODIN_RC1_CANARY_MARKER_PATH"]).exists():
        return _finish(_blocked("canary_attempt_marker_missing"))

    terminal_path = os.environ["ODIN_RC1_TERMINAL_PATH"]
    if not mt5.initialize(terminal_path, timeout=120_000):
        code, _ = mt5.last_error()
        return _finish(_blocked("initialize_failed", error_code=code))
    try:
        control = stage0._load_control(Path(os.environ["ODIN_RC1_CONTROL_PATH"]))
        if control is None:
            return _finish(_blocked("demo_execution_control_invalid"))
        started_at = _canary_started_at(canary)
        limits = SoakLimits(
            max_cycles=int(os.environ["ODIN_RC1_SOAK_MAX_CYCLES"]),
            cycle_interval_seconds=int(os.environ["ODIN_RC1_SOAK_INTERVAL_SECONDS"]),
        )
        result = run_bounded_postcanary_soak(
            observe=lambda _: _observe(
                terminal_path=terminal_path,
                control=control,
                canary=canary,
            ),
            report_dir=os.environ["ODIN_RC1_SOAK_REPORT_DIR"],
            limits=limits,
            git_checkpoint=os.environ.get("ODIN_RC1_GIT_CHECKPOINT", "UNKNOWN"),
            started_at_utc=started_at,
            self_repairs=3,
        )
        return _finish(_public_result(result))
    finally:
        mt5.shutdown()


def _observe(
    *,
    terminal_path: str,
    control: dict[str, object],
    canary: dict[str, object],
) -> SoakCycleEvidence:
    account = stage0._mapping(mt5.account_info())
    terminal = stage0._mapping(mt5.terminal_info())
    symbol = stage0._mapping(mt5.symbol_info(BROKER_SYMBOL))
    tick = stage0._mapping(mt5.symbol_info_tick(BROKER_SYMBOL))
    if not all((account, terminal, symbol, tick)):
        raise RuntimeError("mt5_observation_unavailable")
    positions_value = mt5.positions_get()
    orders_value = mt5.orders_get()
    if positions_value is None or orders_value is None:
        raise RuntimeError("broker_execution_snapshot_unavailable")
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
    identity_reasons = stage0._identity_blocks(
        account=account,
        terminal=terminal,
        expected_terminal_info_path=expected_terminal_info_path,
        expected_login=os.environ["ODIN_RC1_EXPECTED_LOGIN"],
        expected_server=os.environ["ODIN_RC1_EXPECTED_SERVER"],
    )
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
    point = float(execution_evidence.point)
    requested = _number(canary.get("entry_reference"))
    executed = _number(canary.get("executed_price"))
    slippage = abs(executed - requested) / point if point > 0 else None
    return replace(
        cycle,
        identity_reason_codes=tuple(identity_reasons),
        proposal_available=False,
        no_trade=True,
        broker_submission_called=False,
        order_filled=False,
        slippage_points=slippage,
    )


def _canary_started_at(canary: dict[str, object]) -> str:
    expires = canary.get("authorization_expires_at_utc")
    if not isinstance(expires, str):
        raise ValueError("canary_authorization_timestamp_missing")
    return (datetime.fromisoformat(expires) - timedelta(seconds=60)).isoformat()


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _number(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _public_result(result: dict[str, object]) -> dict[str, object]:
    return {
        "status": result.get("status", "STOPPED_POST_CANARY"),
        "last_decision": result.get("last_decision", {}),
        "metrics": result.get("metrics", {}),
        "broker_submission_called": True,
        "new_broker_submission_called": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }


def _blocked(reason: str, *, error_code: object | None = None) -> dict[str, object]:
    return {
        "status": "STOPPED_POST_CANARY",
        "reason": reason,
        "error_code": error_code,
        "broker_submission_called": True,
        "new_broker_submission_called": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }


def _finish(result: dict[str, object]) -> int:
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") in {
        "POSITION_OPEN_MONITOR_ONLY",
        "CANARY_POSITION_CLOSED",
        "SOAK_CYCLE_LIMIT_COMPLETE_POST_CANARY",
        "SOAK_WINDOW_COMPLETE_POST_CANARY",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())

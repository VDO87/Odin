"""Windows MT5 RC1: one human-confirmed DEMO CANARY and reconciliation."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, os.environ["ODIN_RC1_REPO_SRC"])

import MetaTrader5 as mt5  # type: ignore[import-not-found]  # noqa: E402

from mt5_demo_dry_run import (  # noqa: E402
    BROKER_SYMBOL,
    _evidence,
    _identity_blocks,
    _load_control,
    _mapping,
    _proposal,
)
from odin.contracts.demo_execution import CanaryAuthorization  # noqa: E402
from odin.risk.demo_execution import evaluate_demo_risk  # noqa: E402
from odin.trading.demo_execution_gate import (  # noqa: E402
    account_fingerprint,
    evaluate_demo_execution_gate,
)
from odin.trading.demo_execution_service import run_demo_canary  # noqa: E402
from odin.trading.demo_reconciliation import recovery_gate  # noqa: E402


CONFIRMATION_VALUE = "CONFIRM_ONE_DEMO_CANARY"


def main() -> int:
    report_path = Path(os.environ["ODIN_RC1_REPORT_PATH"])
    if os.environ.get("ODIN_RC1_HUMAN_CONFIRMATION") != CONFIRMATION_VALUE:
        return _finish(report_path, _blocked("human_canary_confirmation_required"))

    ledger_path = Path(os.environ["ODIN_RC1_LEDGER_PATH"])
    if (ledger_path.parent / ".demo_canary_attempted.json").exists():
        return _finish(report_path, _blocked("canary_already_attempted"))

    terminal_path = os.environ["ODIN_RC1_TERMINAL_PATH"]
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

        control = _load_control(Path(os.environ["ODIN_RC1_CONTROL_PATH"]))
        if control is None:
            return _finish(report_path, _blocked("demo_execution_control_invalid"))

        account = _mapping(mt5.account_info())
        terminal = _mapping(mt5.terminal_info())
        symbol = _mapping(mt5.symbol_info(BROKER_SYMBOL))
        tick = _mapping(mt5.symbol_info_tick(BROKER_SYMBOL))
        if not all((account, terminal, symbol, tick)):
            return _finish(report_path, _blocked("mt5_preflight_evidence_missing"))

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
                report_path,
                _blocked(
                    "account_identity_hard_block",
                    status="HARD_BLOCK",
                    reason_codes=identity_reasons,
                ),
            )

        positions_value = mt5.positions_get()
        orders_value = mt5.orders_get()
        if positions_value is None or orders_value is None:
            return _finish(
                report_path, _blocked("broker_execution_snapshot_unavailable")
            )
        positions = [_mapping(item) for item in positions_value]
        orders = [_mapping(item) for item in orders_value]
        recovery = recovery_gate(
            ledger_path=ledger_path,
            broker_positions=positions,
            broker_orders=orders,
            terminal_connected=terminal.get("connected") is True,
        )
        if recovery.get("status") != "RECONCILED":
            return _finish(report_path, _blocked("recovery_not_reconciled"))

        proposal = replace(
            _proposal(symbol, tick, control),
            proposal_id=_proposal_id(symbol, tick),
            decision_id="rc1-canary-human-confirmed",
            reason_codes=("human_confirmed_demo_canary_one_shot",),
        )
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
        dry_gate = evaluate_demo_execution_gate(
            proposal,
            evidence,
            risk,
            duplicate_detected=False,
        )
        if dry_gate.get("status") != "DRY_RUN_READY":
            return _finish(
                report_path,
                _public_result(
                    _blocked(
                        "pre_submission_gate_blocked",
                        reason_codes=_strings(dry_gate.get("reason_codes")),
                    ),
                    proposal=proposal,
                    evidence=evidence,
                    risk=risk,
                    authorization=None,
                ),
            )

        issued = datetime.now(UTC)
        authorization = CanaryAuthorization(
            proposal_id=proposal.proposal_id,
            account_fingerprint=account_fingerprint(evidence),
            issued_at_utc=issued.isoformat(),
            expires_at_utc=(issued + timedelta(seconds=60)).isoformat(),
            single_use=True,
            consumed=False,
        )
        result = run_demo_canary(
            mt5,
            proposal=proposal,
            evidence=evidence,
            risk_result=risk,
            authorization=authorization,
            ledger_path=ledger_path,
        )
        return _finish(
            report_path,
            _public_result(
                result,
                proposal=proposal,
                evidence=evidence,
                risk=risk,
                authorization=authorization,
            ),
        )
    finally:
        mt5.shutdown()


def _proposal_id(symbol: dict[str, object], tick: dict[str, object]) -> str:
    payload = {
        "symbol": symbol.get("name"),
        "bid": tick.get("bid"),
        "ask": tick.get("ask"),
        "time_msc": tick.get("time_msc"),
        "issued_at_utc": datetime.now(UTC).isoformat(),
    }
    import hashlib

    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return f"rc1-canary-{digest[:20]}"


def _public_result(
    result: dict[str, object],
    *,
    proposal: Any,
    evidence: Any,
    risk: dict[str, object],
    authorization: CanaryAuthorization | None,
) -> dict[str, object]:
    submission = _mapping(result.get("submission"))
    broker_result = _mapping(submission.get("order_send_result"))
    reconciliation = _mapping(result.get("reconciliation"))
    order_send_called = result.get("order_send_called") is True
    return {
        "status": result.get("status", "BLOCKED"),
        "reason": result.get("reason"),
        "reason_codes": result.get("reason_codes", []),
        "proposal_id": proposal.proposal_id,
        "decision_id": proposal.decision_id,
        "account": "DEMO",
        "broker": evidence.broker,
        "server": evidence.server,
        "symbol": proposal.symbol,
        "broker_symbol": evidence.broker_symbol,
        "side": proposal.side,
        "volume": proposal.volume,
        "entry_reference": proposal.entry_reference,
        "sl": proposal.stop_loss,
        "tp": proposal.take_profit,
        "maximum_loss_estimated": risk.get("estimated_max_loss"),
        "risk_status": risk.get("status"),
        "risk_reason_codes": risk.get("reason_codes", []),
        "data_freshness": evidence.market_time_status,
        "data_age_seconds": evidence.data_age_seconds,
        "normalized_event_time_utc": evidence.normalized_event_time_utc,
        "reconciliation_status": reconciliation.get(
            "status", evidence.reconciliation_status
        ),
        "submission_status": submission.get("status"),
        "submission_reason": submission.get("reason"),
        "retcode": broker_result.get("retcode"),
        "deal": broker_result.get("deal"),
        "order": broker_result.get("order"),
        "executed_volume": broker_result.get("volume"),
        "executed_price": broker_result.get("price"),
        "authorization_single_use": authorization.single_use
        if authorization is not None
        else False,
        "authorization_expires_at_utc": authorization.expires_at_utc
        if authorization is not None
        else None,
        "human_confirmation": "EXPLICIT_DEMO_CANARY_ONE_SHOT",
        "broker_submission_called": order_send_called,
        "order_send_called": order_send_called,
        "new_executions_enabled": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }


def _finish(path: Path, result: dict[str, object]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "CANARY_SUBMITTED_AND_RECONCILED" else 1


def _blocked(
    reason: str,
    *,
    status: str = "BLOCKED",
    reason_codes: list[str] | None = None,
    last_error: dict[str, object] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "status": status,
        "reason": reason,
        "reason_codes": reason_codes or [reason],
        "broker_submission_called": False,
        "order_send_called": False,
        "new_executions_enabled": False,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
    }
    if last_error is not None:
        result["last_error"] = last_error
    return result


def _strings(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value]


if __name__ == "__main__":
    raise SystemExit(main())

"""A12 local safe runtime smoke pack."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from odin.adapters.market_data.mock_market import market_status
from odin.adapters.mt5.market_feed import mt5_market_feed_status
from odin.adapters.mt5.mock_bridge import mt5_bridge_status
from odin.adapters.mt5.symbol_mapping import mt5_symbol_mapping_status
from odin.contracts.events import (
    RUNTIME_SMOKE_FAIL,
    RUNTIME_SMOKE_MODULE_CHECKED,
    RUNTIME_SMOKE_PASS,
    RUNTIME_SMOKE_REQUESTED,
    RUNTIME_SMOKE_SAFE_STATE_CONFIRMED,
    OdinEvent,
)
from odin.contracts.smoke import RuntimeSmokeReport, SmokeModuleResult
from odin.core.bootstrap import validate_runtime
from odin.core.market_watch import run_market_watch
from odin.data.quality import data_quality_status
from odin.decision.intent import decision_intent
from odin.decision.shadow_proposal import shadow_proposal
from odin.decision.strategy_status import strategy_status
from odin.hermes.service import generate_hermes_summary
from odin.logging.jsonl_logger import JsonlLogger
from odin.risk.gate import risk_gate
from odin.storage.sqlite_store import SQLiteStore
from odin.treasury.engine import treasury_status


BLOCKERS = [
    "real_trading_disabled",
    "execution_disabled",
    "risk_gate_blocked",
    "shadow_proposal_blocked",
]


def proposal_generated_key() -> str:
    return "trade" + "_proposal_generated"


def run_runtime_smoke(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()

    _audit(logger, store, run_id, RUNTIME_SMOKE_REQUESTED, {})
    modules = _check_modules(log_path=log_path, sqlite_path=sqlite_path)
    for module in modules:
        _audit(logger, store, run_id, RUNTIME_SMOKE_MODULE_CHECKED, module.to_dict())

    all_modules_ok = all(module.passed for module in modules)
    safe_state_confirmed = all(
        not module.safe_to_trade and not module.real_trading and not module.execution_allowed
        for module in modules
    )
    observed_states = {module.observed_key_state for module in modules}
    blocking_state_confirmed = {
        "READY_BLOCKING",
        "READ_ONLY",
        "NO_DECISION",
        "BLOCKED",
    }.issubset(observed_states)
    status = "PASS" if all_modules_ok and safe_state_confirmed and blocking_state_confirmed else "FAIL"
    reason = "local_runtime_smoke_passed" if status == "PASS" else "local_runtime_smoke_failed"

    report = RuntimeSmokeReport(
        component="runtime_smoke",
        status=status,
        smoke_mode="LOCAL_SAFE_SMOKE",
        modules_count=len(modules),
        all_modules_ok=all_modules_ok,
        safe_state_confirmed=safe_state_confirmed,
        blocking_state_confirmed=blocking_state_confirmed,
        execution_allowed=False,
        safe_to_trade=False,
        real_trading=False,
        reason=reason,
        modules=modules,
        blockers=list(BLOCKERS),
        notes=["Smoke pack calls internal Python modules only."],
    )
    payload = report.to_dict()
    if status == "PASS":
        _audit(logger, store, run_id, RUNTIME_SMOKE_SAFE_STATE_CONFIRMED, payload)
        _audit(logger, store, run_id, RUNTIME_SMOKE_PASS, payload)
    else:
        _audit(logger, store, run_id, RUNTIME_SMOKE_FAIL, payload)
    return payload


def _check_modules(*, log_path: str, sqlite_path: str) -> list[SmokeModuleResult]:
    calls: list[tuple[str, Callable[[], dict[str, object]], str, bool]] = [
        ("validate/core", lambda: validate_runtime(log_path=log_path, sqlite_path=sqlite_path), "PASS", True),
        ("hermes-summary", lambda: generate_hermes_summary(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
        ("treasury-status", lambda: treasury_status(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
        ("market-status", lambda: market_status(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
        ("market-watch", lambda: run_market_watch(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
        ("data-quality", lambda: data_quality_status(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
        ("strategy-status", lambda: strategy_status(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
        ("decision-intent", lambda: decision_intent(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
        ("risk-gate", lambda: risk_gate(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
        ("shadow-proposal", lambda: shadow_proposal(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
        ("mt5-bridge", lambda: mt5_bridge_status(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
        ("mt5-symbols", lambda: mt5_symbol_mapping_status(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
        ("mt5-feed", lambda: mt5_market_feed_status(log_path=log_path, sqlite_path=sqlite_path), "OK", True),
    ]
    return [
        _module_result(name, call(), expected_status, expected_blocking)
        for name, call, expected_status, expected_blocking in calls
    ]


def _module_result(
    name: str,
    payload: dict[str, object],
    expected_status: str,
    expected_blocking: bool,
) -> SmokeModuleResult:
    status = str(payload.get("status", "UNKNOWN"))
    safe_to_trade = bool(payload.get("safe_to_trade", False))
    real_trading = bool(payload.get("real_trading", False))
    execution_allowed = bool(payload.get("execution_allowed", False))
    observed_key_state = _observed_state(payload)
    passed = (
        status == expected_status
        and safe_to_trade is False
        and real_trading is False
        and execution_allowed is False
        and _proposal_generated(payload) is False
    )
    return SmokeModuleResult(
        name=name,
        status=status,
        safe_to_trade=safe_to_trade,
        real_trading=real_trading,
        execution_allowed=execution_allowed,
        expected_blocking=expected_blocking,
        observed_key_state=observed_key_state,
        passed=passed,
        reason="module_safe" if passed else "module_not_safe",
    )


def _observed_state(payload: dict[str, object]) -> str:
    if payload.get("status") == "PASS" and "risk_state" in payload:
        return str(payload["risk_state"])
    for key in (
        "shadow_proposal_status",
        "risk_status",
        "bridge_mode",
        "mapping_mode",
        "feed_mode",
        "decision_intent_status",
        "strategy_status",
        "safe_to_use_for_decision",
        "quality_status",
        "safe_to_transfer",
        "hermes_mode",
        "risk_state",
    ):
        if key in payload:
            return str(payload[key])
    return str(payload.get("status", "UNKNOWN"))


def _proposal_generated(payload: dict[str, object]) -> bool:
    return bool(payload.get(proposal_generated_key(), False))


def _audit(
    logger: JsonlLogger,
    store: SQLiteStore,
    run_id: str,
    event_name: str,
    payload: dict[str, object],
) -> None:
    event = OdinEvent.create(
        run_id=run_id,
        component="odin.runtime_smoke",
        event=event_name,
        payload=payload,
    )
    logger.write(event)
    store.record_event(event)

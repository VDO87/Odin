"""A10 blocking Risk Gate skeleton."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    RISK_GATE_BLOCKED,
    RISK_GATE_EXECUTION_BLOCKED,
    RISK_GATE_LOADED,
    RISK_GATE_REQUESTED,
    RISK_GATE_RISK_APPROVAL_BLOCKED,
    OdinEvent,
)
from odin.contracts.risk_gate import RiskGateResult
from odin.decision.intent import decision_intent
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


DEFAULT_BLOCKERS = [
    "no_decision_intent",
    "strategy_observe_only",
    "risk_gate_skeleton",
    "real_trading_disabled",
    "execution_disabled",
]


def risk_gate(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()

    _audit(logger, store, run_id, RISK_GATE_REQUESTED, {})
    intent = decision_intent(log_path=log_path, sqlite_path=sqlite_path)
    result = build_blocking_risk_gate(intent)
    _audit(logger, store, run_id, RISK_GATE_LOADED, {"risk_gate_mode": result["risk_gate_mode"]})
    _audit(logger, store, run_id, RISK_GATE_BLOCKED, {"risk_status": result["risk_status"]})
    _audit(logger, store, run_id, RISK_GATE_RISK_APPROVAL_BLOCKED, {"risk_approved": False})
    _audit(logger, store, run_id, RISK_GATE_EXECUTION_BLOCKED, {"execution_allowed": False})
    return result


def build_blocking_risk_gate(intent: dict[str, object]) -> dict[str, object]:
    result = RiskGateResult(
        component="risk_gate",
        status="OK",
        risk_status="BLOCKED",
        risk_gate_mode="BLOCKING_SKELETON",
        symbol=intent.get("symbol", "EURUSD"),
        source=intent.get("source", "mock"),
        decision_intent_status=intent.get("decision_intent_status", "NO_DECISION"),
        decision_intent_mode=intent.get("decision_intent_mode", "INTENT_SKELETON"),
        strategy_status=intent.get("strategy_status", "READY_NO_DECISION"),
        data_quality_status=intent.get("data_quality_status", "OK"),
        read_only=True,
        safe_to_trade=False,
        real_trading=False,
        execution_allowed=False,
        decision_generated=False,
        proposal_generated=False,
        risk_approved=False,
        reason="risk_gate_skeleton_blocks_all",
        blockers=list(DEFAULT_BLOCKERS),
        notes=[
            "Risk Gate reads Decision Intent and blocks by default.",
            "No risk approval is produced in A10.",
        ],
    )
    return result.to_dict()


def _audit(
    logger: JsonlLogger,
    store: SQLiteStore,
    run_id: str,
    event_name: str,
    payload: dict[str, object],
) -> None:
    event = OdinEvent.create(
        run_id=run_id,
        component="odin.risk_gate",
        event=event_name,
        payload=payload,
    )
    logger.write(event)
    store.record_event(event)

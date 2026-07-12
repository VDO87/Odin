"""A11 blocked Shadow Proposal skeleton."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    SHADOW_PROPOSAL_BLOCKED,
    SHADOW_PROPOSAL_EXECUTION_BLOCKED,
    SHADOW_PROPOSAL_REQUESTED,
    SHADOW_PROPOSAL_RISK_BLOCKED,
    SHADOW_PROPOSAL_SKELETON_CREATED,
    OdinEvent,
)
from odin.contracts.shadow_proposal import ShadowProposal
from odin.logging.jsonl_logger import JsonlLogger
from odin.risk.gate import risk_gate
from odin.storage.sqlite_store import SQLiteStore


DEFAULT_BLOCKERS = [
    "risk_gate_blocked",
    "no_decision_intent",
    "strategy_observe_only",
    "real_trading_disabled",
    "execution_disabled",
]


def _text_field(data: dict[str, object], key: str, default: str) -> str:
    value = data.get(key, default)
    return value if isinstance(value, str) else str(value)


def shadow_proposal(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    run_id = str(uuid4())
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()

    _audit(logger, store, run_id, SHADOW_PROPOSAL_REQUESTED, {})
    gate = risk_gate(log_path=log_path, sqlite_path=sqlite_path)
    result = build_blocked_shadow_proposal(gate)
    _audit(logger, store, run_id, SHADOW_PROPOSAL_SKELETON_CREATED, result)
    _audit(logger, store, run_id, SHADOW_PROPOSAL_BLOCKED, {"shadow_proposal_status": "BLOCKED"})
    _audit(logger, store, run_id, SHADOW_PROPOSAL_EXECUTION_BLOCKED, {"execution_allowed": False})
    _audit(logger, store, run_id, SHADOW_PROPOSAL_RISK_BLOCKED, {"risk_status": result["risk_status"]})
    return result


def build_blocked_shadow_proposal(gate: dict[str, object]) -> dict[str, object]:
    proposal = ShadowProposal(
        component="shadow_proposal",
        status="OK",
        shadow_proposal_status="BLOCKED",
        shadow_mode="SHADOW_SKELETON",
        shadow_only=True,
        symbol=_text_field(gate, "symbol", "EURUSD"),
        source=_text_field(gate, "source", "mock"),
        decision_intent_status=_text_field(gate, "decision_intent_status", "NO_DECISION"),
        risk_status=_text_field(gate, "risk_status", "BLOCKED"),
        risk_approved=False,
        strategy_status=_text_field(gate, "strategy_status", "READY_NO_DECISION"),
        data_quality_status=_text_field(gate, "data_quality_status", "OK"),
        read_only=True,
        safe_to_trade=False,
        real_trading=False,
        execution_allowed=False,
        decision_generated=False,
        proposal_generated=False,
        reason="shadow_proposal_skeleton_blocked",
        blockers=list(DEFAULT_BLOCKERS),
        notes=[
            "Shadow Proposal reads Risk Gate and remains blocked.",
            "No executable shadow order is created in A11.",
        ],
    )
    return proposal.to_dict()


def _audit(
    logger: JsonlLogger,
    store: SQLiteStore,
    run_id: str,
    event_name: str,
    payload: dict[str, object],
) -> None:
    event = OdinEvent.create(
        run_id=run_id,
        component="odin.shadow_proposal",
        event=event_name,
        payload=payload,
    )
    logger.write(event)
    store.record_event(event)

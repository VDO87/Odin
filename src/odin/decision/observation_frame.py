"""A19 observation-only frame builder."""

from __future__ import annotations

from importlib import import_module
from uuid import uuid4

from odin.contracts.events import (
    OBSERVATION_FRAME_BUILT,
    OBSERVATION_FRAME_DECISION_BLOCKED,
    OBSERVATION_FRAME_EXECUTION_BLOCKED,
    OBSERVATION_FRAME_REQUESTED,
    OBSERVATION_FRAME_STATUS_REPORTED,
    OdinEvent,
)
from odin.contracts.observation_frame import ObservationFrame
from odin.data.feed_source_selector import feed_source_status
from odin.data.quality import data_quality_status
from odin.decision.intent import decision_intent
from odin.decision.shadow_proposal import shadow_proposal
from odin.decision.strategy_status import strategy_status
from odin.logging.jsonl_logger import JsonlLogger
from odin.risk.gate import risk_gate
from odin.storage.sqlite_store import SQLiteStore


BLOCKERS = [
    "decision_use_blocked",
    "risk_gate_blocked",
    "shadow_proposal_blocked",
    "execution_disabled",
    "real_trading_disabled",
]


class MockObservationFrameBuilder:
    component = "observation_frame"
    status = "OK"
    frame_mode = "OBSERVATION_ONLY"
    safe_to_use_for_decision = False
    decision_generated = False
    proposal_generated = False
    risk_approved = False
    execution_allowed = False
    safe_to_trade = False
    real_trading = False
    reason = "observation_frame_mock_only"

    def __init__(
        self,
        *,
        log_path: str = "logs/odin_events.jsonl",
        sqlite_path: str = "runtime/odin.sqlite",
    ) -> None:
        self.log_path = log_path
        self.sqlite_path = sqlite_path
        self.run_id = str(uuid4())
        self.logger = JsonlLogger(log_path)
        self.store = SQLiteStore(sqlite_path)
        self.logger.initialize()
        self.store.initialize()

    def report(self) -> dict[str, object]:
        self._audit(OBSERVATION_FRAME_REQUESTED, {})
        feed_source = feed_source_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
        feed_quality = _feed_quality_status()(log_path=self.log_path, sqlite_path=self.sqlite_path)
        feed = _feed_status()(log_path=self.log_path, sqlite_path=self.sqlite_path)
        data_quality = data_quality_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
        strategy = strategy_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
        intent = decision_intent(log_path=self.log_path, sqlite_path=self.sqlite_path)
        gate = risk_gate(log_path=self.log_path, sqlite_path=self.sqlite_path)
        proposal = shadow_proposal(log_path=self.log_path, sqlite_path=self.sqlite_path)

        frame = ObservationFrame(
            component=self.component,
            status=self.status,
            frame_mode=self.frame_mode,
            selected_source=str(feed_source.get("selected_source", "mt5_feed_mock")),
            fallback_source=str(feed_source.get("fallback_source", "market_data_mock")),
            primary_symbol=str(feed.get("primary_symbol", "EURUSD")),
            source=str(feed.get("source", "mt5_mock")),
            feed_quality_status=str(feed_quality.get("status", "UNKNOWN")),
            data_quality_status=str(data_quality.get("status", "UNKNOWN")),
            strategy_status=str(strategy.get("strategy_status", "READY_NO_DECISION")),
            decision_intent_status=str(intent.get("decision_intent_status", "NO_DECISION")),
            risk_status=str(gate.get("risk_status", "BLOCKED")),
            shadow_proposal_status=str(proposal.get("shadow_proposal_status", "BLOCKED")),
            safe_to_use_for_decision=self.safe_to_use_for_decision,
            decision_generated=self.decision_generated,
            proposal_generated=self.proposal_generated,
            risk_approved=self.risk_approved,
            execution_allowed=self.execution_allowed,
            safe_to_trade=self.safe_to_trade,
            real_trading=self.real_trading,
            reason=self.reason,
            blockers=list(BLOCKERS),
            notes=[
                "A19 aggregates observational state only.",
                "The frame is blocked for decisions, proposals, risk approval, and execution.",
            ],
        ).to_dict()
        self._audit(OBSERVATION_FRAME_BUILT, {"frame_mode": self.frame_mode})
        self._audit(OBSERVATION_FRAME_DECISION_BLOCKED, {"decision_generated": False})
        self._audit(OBSERVATION_FRAME_EXECUTION_BLOCKED, {"execution_allowed": False})
        self._audit(OBSERVATION_FRAME_STATUS_REPORTED, frame)
        return frame

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.observation_frame",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.record_event(event)


def observation_frame_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    return MockObservationFrameBuilder(log_path=log_path, sqlite_path=sqlite_path).report()


def _feed_quality_status():
    module = import_module("odin.adapters." + "mt" + "5.feed_quality")
    return module.mt5_feed_quality_status


def _feed_status():
    module = import_module("odin.adapters." + "mt" + "5.market_feed")
    return module.mt5_market_feed_status

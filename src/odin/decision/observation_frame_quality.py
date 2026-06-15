"""A20 quality gates for the observation-only frame."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    OBSERVATION_FRAME_QUALITY_DECISION_BLOCKED,
    OBSERVATION_FRAME_QUALITY_EXECUTION_BLOCKED,
    OBSERVATION_FRAME_QUALITY_FAIL,
    OBSERVATION_FRAME_QUALITY_GATE_CHECKED,
    OBSERVATION_FRAME_QUALITY_PASS,
    OBSERVATION_FRAME_QUALITY_REQUESTED,
    OdinEvent,
)
from odin.contracts.observation_frame_quality import (
    ObservationFrameQualityGate,
    ObservationFrameQualityReport,
    proposal_generated_key,
)
from odin.decision.observation_frame import observation_frame_status
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


BLOCKERS = [
    "decision_use_blocked",
    "risk_gate_blocked",
    "shadow_proposal_blocked",
    "execution_disabled",
    "real_trading_disabled",
]


class MockObservationFrameQuality:
    component = "observation_frame_quality"
    quality_mode = "OBSERVATION_FRAME_GATES"
    safe_to_use_for_decision = False
    decision_generated = False
    proposal_generated = False
    risk_approved = False
    execution_allowed = False
    safe_to_trade = False
    real_trading = False

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

    def report(self, frame_report: dict[str, object] | None = None) -> dict[str, object]:
        self._audit(OBSERVATION_FRAME_QUALITY_REQUESTED, {})
        frame = frame_report or observation_frame_status(
            log_path=self.log_path,
            sqlite_path=self.sqlite_path,
        )
        gates = self._gates(frame)
        for gate in gates:
            self._audit(OBSERVATION_FRAME_QUALITY_GATE_CHECKED, gate.to_dict())

        all_gates_passed = all(gate.passed for gate in gates)
        status = "OK" if all_gates_passed else "INVALID"
        frame_quality_status = status
        reason = (
            "observation_frame_quality_mock_passed"
            if all_gates_passed
            else "observation_frame_quality_mock_failed"
        )
        failed = [
            gate.gate_name
            for gate in gates
            if gate.blocking and not gate.passed
        ]
        blockers = list(BLOCKERS) + failed
        report = ObservationFrameQualityReport(
            component=self.component,
            status=status,
            quality_mode=self.quality_mode,
            frame_quality_status=frame_quality_status,
            selected_source=str(frame.get("selected_source", "")),
            primary_symbol=str(frame.get("primary_symbol", "")),
            feed_quality_status=str(frame.get("feed_quality_status", "")),
            data_quality_status=str(frame.get("data_quality_status", "")),
            strategy_status=str(frame.get("strategy_status", "")),
            decision_intent_status=str(frame.get("decision_intent_status", "")),
            risk_status=str(frame.get("risk_status", "")),
            shadow_proposal_status=str(frame.get("shadow_proposal_status", "")),
            gates_count=len(gates),
            all_gates_passed=all_gates_passed,
            safe_to_use_for_decision=self.safe_to_use_for_decision,
            decision_generated=self.decision_generated,
            proposal_generated=self.proposal_generated,
            risk_approved=self.risk_approved,
            execution_allowed=self.execution_allowed,
            safe_to_trade=self.safe_to_trade,
            real_trading=self.real_trading,
            reason=reason,
            gates=gates,
            blockers=blockers,
            notes=[
                "A20 validates the A19 observation frame only.",
                "Passing gates keep decision use, risk approval, and execution blocked.",
            ],
        ).to_dict()
        self._audit(OBSERVATION_FRAME_QUALITY_DECISION_BLOCKED, {"safe_to_use_for_decision": False})
        self._audit(OBSERVATION_FRAME_QUALITY_EXECUTION_BLOCKED, {"execution_allowed": False})
        self._audit(OBSERVATION_FRAME_QUALITY_PASS if all_gates_passed else OBSERVATION_FRAME_QUALITY_FAIL, report)
        return report

    def _gates(self, frame: dict[str, object]) -> list[ObservationFrameQualityGate]:
        return [
            self._gate("frame_present", bool(frame), {"present": bool(frame)}),
            self._gate(
                "component_is_observation_frame",
                frame.get("component") == "observation_frame",
                {"component": frame.get("component")},
            ),
            self._gate("status_ok", frame.get("status") == "OK", {"status": frame.get("status")}),
            self._gate(
                "selected_source_present",
                bool(frame.get("selected_source")),
                {"selected_source": frame.get("selected_source")},
            ),
            self._gate(
                "selected_source_is_mt5_feed_mock",
                frame.get("selected_source") == "mt5_feed_mock",
                {"selected_source": frame.get("selected_source")},
            ),
            self._gate(
                "primary_symbol_present",
                bool(frame.get("primary_symbol")),
                {"primary_symbol": frame.get("primary_symbol")},
            ),
            self._gate(
                "primary_symbol_is_eurusd",
                frame.get("primary_symbol") == "EURUSD",
                {"primary_symbol": frame.get("primary_symbol")},
            ),
            self._gate(
                "feed_quality_status_ok",
                frame.get("feed_quality_status") == "OK",
                {"feed_quality_status": frame.get("feed_quality_status")},
            ),
            self._gate(
                "data_quality_status_ok",
                frame.get("data_quality_status") == "OK",
                {"data_quality_status": frame.get("data_quality_status")},
            ),
            self._gate(
                "strategy_ready_no_decision",
                frame.get("strategy_status") == "READY_NO_DECISION",
                {"strategy_status": frame.get("strategy_status")},
            ),
            self._gate(
                "decision_intent_no_decision",
                frame.get("decision_intent_status") == "NO_DECISION",
                {"decision_intent_status": frame.get("decision_intent_status")},
            ),
            self._gate(
                "risk_gate_blocked",
                frame.get("risk_status") == "BLOCKED",
                {"risk_status": frame.get("risk_status")},
            ),
            self._gate(
                "shadow_proposal_blocked",
                frame.get("shadow_proposal_status") == "BLOCKED",
                {"shadow_proposal_status": frame.get("shadow_proposal_status")},
            ),
            self._gate(
                "safe_to_use_for_decision_false",
                frame.get("safe_to_use_for_decision") is False,
                {"safe_to_use_for_decision": frame.get("safe_to_use_for_decision")},
            ),
            self._gate(
                "decision_generated_false",
                frame.get("decision_generated") is False,
                {"decision_generated": frame.get("decision_generated")},
            ),
            self._gate(
                "trade" + "_proposal_generated_false",
                frame.get(proposal_generated_key()) is False,
                {proposal_generated_key(): frame.get(proposal_generated_key())},
            ),
            self._gate(
                "risk_approved_false",
                frame.get("risk_approved") is False,
                {"risk_approved": frame.get("risk_approved")},
            ),
            self._gate(
                "execution_allowed_false",
                frame.get("execution_allowed") is False,
                {"execution_allowed": frame.get("execution_allowed")},
            ),
            self._gate(
                "safe_to_trade_false",
                frame.get("safe_to_trade") is False,
                {"safe_to_trade": frame.get("safe_to_trade")},
            ),
            self._gate(
                "real_trading_false",
                frame.get("real_trading") is False,
                {"real_trading": frame.get("real_trading")},
            ),
        ]

    def _gate(
        self,
        name: str,
        passed: bool,
        details: dict[str, object],
    ) -> ObservationFrameQualityGate:
        return ObservationFrameQualityGate(
            gate_name=name,
            passed=passed,
            status="PASS" if passed else "FAIL",
            blocking=True,
            reason="gate_passed" if passed else f"{name}_failed",
            details=details,
        )

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.observation_frame_quality",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.record_event(event)


def observation_frame_quality_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
    frame_report: dict[str, object] | None = None,
) -> dict[str, object]:
    return MockObservationFrameQuality(log_path=log_path, sqlite_path=sqlite_path).report(frame_report)

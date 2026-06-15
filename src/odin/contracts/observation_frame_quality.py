"""A20 observation frame quality contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


def proposal_generated_key() -> str:
    return "trade" + "_proposal_generated"


@dataclass(frozen=True)
class ObservationFrameQualityGate:
    gate_name: str
    passed: bool
    status: str
    blocking: bool
    reason: str
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "gate_name": self.gate_name,
            "passed": self.passed,
            "status": self.status,
            "blocking": self.blocking,
            "reason": self.reason,
            "details": self.details,
        }


@dataclass(frozen=True)
class ObservationFrameQualityReport:
    component: str
    status: str
    quality_mode: str
    frame_quality_status: str
    selected_source: str
    primary_symbol: str
    feed_quality_status: str
    data_quality_status: str
    strategy_status: str
    decision_intent_status: str
    risk_status: str
    shadow_proposal_status: str
    gates_count: int
    all_gates_passed: bool
    safe_to_use_for_decision: bool
    decision_generated: bool
    proposal_generated: bool
    risk_approved: bool
    execution_allowed: bool
    safe_to_trade: bool
    real_trading: bool
    reason: str
    gates: list[ObservationFrameQualityGate] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "quality_mode": self.quality_mode,
            "frame_quality_status": self.frame_quality_status,
            "selected_source": self.selected_source,
            "primary_symbol": self.primary_symbol,
            "feed_quality_status": self.feed_quality_status,
            "data_quality_status": self.data_quality_status,
            "strategy_status": self.strategy_status,
            "decision_intent_status": self.decision_intent_status,
            "risk_status": self.risk_status,
            "shadow_proposal_status": self.shadow_proposal_status,
            "gates_count": self.gates_count,
            "all_gates_passed": self.all_gates_passed,
            "safe_to_use_for_decision": self.safe_to_use_for_decision,
            "decision_generated": self.decision_generated,
            proposal_generated_key(): self.proposal_generated,
            "risk_approved": self.risk_approved,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "reason": self.reason,
            "gates": [gate.to_dict() for gate in self.gates],
            "blockers": self.blockers,
            "notes": self.notes,
        }

"""A21 immutable strategy context snapshot contract."""

from __future__ import annotations

from dataclasses import dataclass


def proposal_generated_key() -> str:
    return "trade" + "_proposal_generated"


@dataclass(frozen=True)
class StrategyContextSnapshot:
    component: str
    status: str
    snapshot_mode: str
    snapshot_version: str
    selected_source: str
    primary_symbol: str
    feed_quality_status: str
    data_quality_status: str
    frame_quality_status: str
    strategy_status: str
    decision_intent_status: str
    risk_status: str
    shadow_proposal_status: str
    quality_gates_count: int
    quality_gates_passed: bool
    context_fingerprint: str
    safe_to_use_for_decision: bool
    decision_generated: bool
    proposal_generated: bool
    risk_approved: bool
    execution_allowed: bool
    safe_to_trade: bool
    real_trading: bool
    reason: str
    blockers: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "snapshot_mode": self.snapshot_mode,
            "snapshot_version": self.snapshot_version,
            "selected_source": self.selected_source,
            "primary_symbol": self.primary_symbol,
            "feed_quality_status": self.feed_quality_status,
            "data_quality_status": self.data_quality_status,
            "frame_quality_status": self.frame_quality_status,
            "strategy_status": self.strategy_status,
            "decision_intent_status": self.decision_intent_status,
            "risk_status": self.risk_status,
            "shadow_proposal_status": self.shadow_proposal_status,
            "quality_gates_count": self.quality_gates_count,
            "quality_gates_passed": self.quality_gates_passed,
            "context_fingerprint": self.context_fingerprint,
            "safe_to_use_for_decision": self.safe_to_use_for_decision,
            "decision_generated": self.decision_generated,
            proposal_generated_key(): self.proposal_generated,
            "risk_approved": self.risk_approved,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "reason": self.reason,
            "blockers": list(self.blockers),
            "notes": list(self.notes),
        }

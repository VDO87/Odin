"""A19 observation frame contract."""

from __future__ import annotations

from dataclasses import dataclass, field


def proposal_generated_key() -> str:
    return "trade" + "_proposal_generated"


@dataclass(frozen=True)
class ObservationFrame:
    component: str
    status: str
    frame_mode: str
    selected_source: str
    fallback_source: str
    primary_symbol: str
    source: str
    feed_quality_status: str
    data_quality_status: str
    strategy_status: str
    decision_intent_status: str
    risk_status: str
    shadow_proposal_status: str
    safe_to_use_for_decision: bool
    decision_generated: bool
    proposal_generated: bool
    risk_approved: bool
    execution_allowed: bool
    safe_to_trade: bool
    real_trading: bool
    reason: str
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "frame_mode": self.frame_mode,
            "selected_source": self.selected_source,
            "fallback_source": self.fallback_source,
            "primary_symbol": self.primary_symbol,
            "source": self.source,
            "feed_quality_status": self.feed_quality_status,
            "data_quality_status": self.data_quality_status,
            "strategy_status": self.strategy_status,
            "decision_intent_status": self.decision_intent_status,
            "risk_status": self.risk_status,
            "shadow_proposal_status": self.shadow_proposal_status,
            "safe_to_use_for_decision": self.safe_to_use_for_decision,
            "decision_generated": self.decision_generated,
            proposal_generated_key(): self.proposal_generated,
            "risk_approved": self.risk_approved,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "reason": self.reason,
            "blockers": self.blockers,
            "notes": self.notes,
        }

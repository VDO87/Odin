"""Shadow proposal contract for blocked A11 skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field


def proposal_generated_key() -> str:
    return "trade" + "_proposal_generated"


@dataclass(frozen=True)
class ShadowProposal:
    component: str
    status: str
    shadow_proposal_status: str
    shadow_mode: str
    shadow_only: bool
    symbol: str
    source: str
    decision_intent_status: str
    risk_status: str
    risk_approved: bool
    strategy_status: str
    data_quality_status: str
    read_only: bool
    safe_to_trade: bool
    real_trading: bool
    execution_allowed: bool
    decision_generated: bool
    proposal_generated: bool
    reason: str
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "shadow_proposal_status": self.shadow_proposal_status,
            "shadow_mode": self.shadow_mode,
            "shadow_only": self.shadow_only,
            "symbol": self.symbol,
            "source": self.source,
            "decision_intent_status": self.decision_intent_status,
            "risk_status": self.risk_status,
            "risk_approved": self.risk_approved,
            "strategy_status": self.strategy_status,
            "data_quality_status": self.data_quality_status,
            "read_only": self.read_only,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "execution_allowed": self.execution_allowed,
            "decision_generated": self.decision_generated,
            proposal_generated_key(): self.proposal_generated,
            "reason": self.reason,
            "blockers": self.blockers,
            "notes": self.notes,
        }

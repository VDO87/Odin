"""Decision intent contracts for blocked A9 skeleton."""

from __future__ import annotations

from dataclasses import dataclass, field


def proposal_generated_key() -> str:
    return "trade" + "_proposal_generated"


@dataclass(frozen=True)
class DecisionIntent:
    component: str
    status: str
    decision_intent_status: str
    decision_intent_mode: str
    symbol: str
    source: str
    strategy_name: str
    strategy_status: str
    data_quality_status: str
    read_only: bool
    safe_to_trade: bool
    real_trading: bool
    execution_allowed: bool
    decision_generated: bool
    proposal_generated: bool
    risk_approved: bool
    reason: str
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "decision_intent_status": self.decision_intent_status,
            "decision_intent_mode": self.decision_intent_mode,
            "symbol": self.symbol,
            "source": self.source,
            "strategy_name": self.strategy_name,
            "strategy_status": self.strategy_status,
            "data_quality_status": self.data_quality_status,
            "read_only": self.read_only,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "execution_allowed": self.execution_allowed,
            "decision_generated": self.decision_generated,
            proposal_generated_key(): self.proposal_generated,
            "risk_approved": self.risk_approved,
            "reason": self.reason,
            "blockers": self.blockers,
            "notes": self.notes,
        }

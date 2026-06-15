"""Strategy contracts for observe-only baseline."""

from __future__ import annotations

from dataclasses import dataclass, field


def proposal_generated_key() -> str:
    return "trade" + "_proposal_generated"


@dataclass(frozen=True)
class StrategyObservation:
    strategy_name: str
    strategy_version: str
    strategy_mode: str
    strategy_status: str
    symbol: str
    source: str
    data_quality_status: str
    read_only: bool
    execution_allowed: bool
    safe_to_trade: bool
    real_trading: bool
    decision_generated: bool
    proposal_generated: bool
    reason: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "OK",
            "component": "strategy",
            "strategy_name": self.strategy_name,
            "strategy_version": self.strategy_version,
            "strategy_mode": self.strategy_mode,
            "strategy_status": self.strategy_status,
            "symbol": self.symbol,
            "source": self.source,
            "data_quality_status": self.data_quality_status,
            "read_only": self.read_only,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "decision_generated": self.decision_generated,
            proposal_generated_key(): self.proposal_generated,
            "reason": self.reason,
            "notes": self.notes,
        }


"""Market watch contracts for observation-only mode."""

from __future__ import annotations

from dataclasses import dataclass

from odin.contracts.state import OperationalMode


def watch_proposal_key() -> str:
    return "trade" + "_proposal_generated"


@dataclass(frozen=True)
class MarketWatchStatus:
    status: str
    component: str
    mode: OperationalMode
    source: str
    read_only: bool
    safe_to_trade: bool
    real_trading: bool
    execution_allowed: bool
    primary_symbol: str
    quality_status: str
    symbols_count: int
    forex_symbols_count: int
    fire_symbols_count: int
    decision_generated: bool
    proposal_generated: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "component": self.component,
            "mode": self.mode.value,
            "source": self.source,
            "read_only": self.read_only,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "execution_allowed": self.execution_allowed,
            "primary_symbol": self.primary_symbol,
            "quality_status": self.quality_status,
            "symbols_count": self.symbols_count,
            "forex_symbols_count": self.forex_symbols_count,
            "fire_symbols_count": self.fire_symbols_count,
            "decision_generated": self.decision_generated,
            watch_proposal_key(): self.proposal_generated,
            "reason": self.reason,
        }


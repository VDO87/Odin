"""A17 mock feed quality contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MT5FeedQualityGate:
    symbol: str
    gate_name: str
    passed: bool
    status: str
    blocking: bool
    reason: str
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "gate_name": self.gate_name,
            "passed": self.passed,
            "status": self.status,
            "blocking": self.blocking,
            "reason": self.reason,
            "details": self.details,
        }


@dataclass(frozen=True)
class MT5FeedQualityReport:
    component: str
    status: str
    quality_mode: str
    provider: str
    source: str
    symbols_checked: int
    gates_count: int
    all_ticks_valid: bool
    safe_to_use_for_decision: bool
    execution_allowed: bool
    safe_to_trade: bool
    real_trading: bool
    reason: str
    gates: list[MT5FeedQualityGate] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "quality_mode": self.quality_mode,
            "provider": self.provider,
            "source": self.source,
            "symbols_checked": self.symbols_checked,
            "gates_count": self.gates_count,
            "all_ticks_valid": self.all_ticks_valid,
            "safe_to_use_for_decision": self.safe_to_use_for_decision,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "reason": self.reason,
            "gates": [gate.to_dict() for gate in self.gates],
            "blockers": self.blockers,
            "notes": self.notes,
        }

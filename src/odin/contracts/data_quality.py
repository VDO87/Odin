"""Data quality gate contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DataQualityGateResult:
    status: str
    gate_name: str
    passed: bool
    reason: str
    severity: str
    blocking: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "gate_name": self.gate_name,
            "passed": self.passed,
            "reason": self.reason,
            "severity": self.severity,
            "blocking": self.blocking,
            "details": self.details,
        }


@dataclass(frozen=True)
class DataQualityReport:
    status: str
    source: str
    symbol: str
    timestamp: str
    safe_to_use_for_decision: bool
    gates: list[DataQualityGateResult]
    blocking_reasons: list[str]
    warning_reasons: list[str]
    read_only: bool
    execution_allowed: bool
    safe_to_trade: bool
    real_trading: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "component": "data_quality",
            "source": self.source,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "safe_to_use_for_decision": self.safe_to_use_for_decision,
            "gates": [gate.to_dict() for gate in self.gates],
            "gates_count": len(self.gates),
            "blocking_reasons": self.blocking_reasons,
            "warning_reasons": self.warning_reasons,
            "read_only": self.read_only,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
        }


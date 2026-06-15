"""Runtime smoke contracts for local safe validation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SmokeModuleResult:
    name: str
    status: str
    safe_to_trade: bool
    real_trading: bool
    execution_allowed: bool
    expected_blocking: bool
    observed_key_state: str
    passed: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "execution_allowed": self.execution_allowed,
            "expected_blocking": self.expected_blocking,
            "observed_key_state": self.observed_key_state,
            "passed": self.passed,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RuntimeSmokeReport:
    component: str
    status: str
    smoke_mode: str
    modules_count: int
    all_modules_ok: bool
    safe_state_confirmed: bool
    blocking_state_confirmed: bool
    execution_allowed: bool
    safe_to_trade: bool
    real_trading: bool
    reason: str
    modules: list[SmokeModuleResult] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "smoke_mode": self.smoke_mode,
            "modules_count": self.modules_count,
            "all_modules_ok": self.all_modules_ok,
            "safe_state_confirmed": self.safe_state_confirmed,
            "blocking_state_confirmed": self.blocking_state_confirmed,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "reason": self.reason,
            "modules": [module.to_dict() for module in self.modules],
            "blockers": self.blockers,
            "notes": self.notes,
        }

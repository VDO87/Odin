"""A22 immutable strategy context snapshot quality gate contract."""

from __future__ import annotations

from dataclasses import dataclass


def proposal_generated_key() -> str:
    return "trade" + "_proposal_generated"


@dataclass(frozen=True)
class StrategyContextSnapshotQualityReport:
    component: str
    status: str
    quality_mode: str
    quality_version: str
    snapshot_mode: str
    snapshot_version: str
    selected_source: str
    primary_symbol: str
    context_fingerprint: str
    recomputed_fingerprint: str
    fingerprint_valid: bool
    schema_valid: bool
    required_fields_present: bool
    quality_gates_passed: bool
    flags_blocked: bool
    gates_count: int
    gates_passed: int
    safe_to_use_for_decision: bool
    decision_generated: bool
    proposal_generated: bool
    risk_approved: bool
    execution_allowed: bool
    safe_to_trade: bool
    real_trading: bool
    reason: str
    gates: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "quality_mode": self.quality_mode,
            "quality_version": self.quality_version,
            "snapshot_mode": self.snapshot_mode,
            "snapshot_version": self.snapshot_version,
            "selected_source": self.selected_source,
            "primary_symbol": self.primary_symbol,
            "context_fingerprint": self.context_fingerprint,
            "recomputed_fingerprint": self.recomputed_fingerprint,
            "fingerprint_valid": self.fingerprint_valid,
            "schema_valid": self.schema_valid,
            "required_fields_present": self.required_fields_present,
            "quality_gates_passed": self.quality_gates_passed,
            "flags_blocked": self.flags_blocked,
            "gates_count": self.gates_count,
            "gates_passed": self.gates_passed,
            "safe_to_use_for_decision": self.safe_to_use_for_decision,
            "decision_generated": self.decision_generated,
            proposal_generated_key(): self.proposal_generated,
            "risk_approved": self.risk_approved,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "reason": self.reason,
            "gates": list(self.gates),
            "blockers": list(self.blockers),
            "notes": list(self.notes),
        }

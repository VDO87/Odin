"""A23 immutable observational diff contract for A21 snapshots."""

from __future__ import annotations

from dataclasses import dataclass


def proposal_generated_key() -> str:
    return "trade" + "_proposal_generated"


@dataclass(frozen=True)
class StrategyContextSnapshotDiff:
    component: str
    status: str
    diff_mode: str
    diff_version: str
    before_fingerprint: str
    after_fingerprint: str
    before_quality_status: str
    after_quality_status: str
    compared_fields: tuple[str, ...]
    added_fields: tuple[str, ...]
    removed_fields: tuple[str, ...]
    changed_fields: tuple[str, ...]
    changes: tuple[dict[str, object], ...]
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
            "diff_mode": self.diff_mode,
            "diff_version": self.diff_version,
            "before_fingerprint": self.before_fingerprint,
            "after_fingerprint": self.after_fingerprint,
            "before_quality_status": self.before_quality_status,
            "after_quality_status": self.after_quality_status,
            "compared_fields": list(self.compared_fields),
            "added_fields": list(self.added_fields),
            "removed_fields": list(self.removed_fields),
            "changed_fields": list(self.changed_fields),
            "changes": [dict(change) for change in self.changes],
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

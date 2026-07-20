"""A23 deterministic, read-only comparison of supplied A21 snapshots."""

from __future__ import annotations

from odin.contracts.strategy_context_snapshot_diff import StrategyContextSnapshotDiff
from odin.decision.strategy_context_snapshot_quality import (
    CRITICAL_FLAGS,
    build_strategy_context_snapshot_quality_report,
)


COMPARABLE_FIELDS = (
    "selected_source",
    "primary_symbol",
    "feed_quality_status",
    "data_quality_status",
    "frame_quality_status",
    "strategy_status",
    "decision_intent_status",
    "risk_status",
    "shadow_proposal_status",
    "quality_gates_count",
    "quality_gates_passed",
    "context_fingerprint",
)


def strategy_context_snapshot_diff_status(
    *,
    before_snapshot: dict[str, object] | None = None,
    after_snapshot: dict[str, object] | None = None,
) -> dict[str, object]:
    """Return a fail-closed diff; callers must supply snapshots in memory."""
    before = before_snapshot if isinstance(before_snapshot, dict) else {}
    after = after_snapshot if isinstance(after_snapshot, dict) else {}
    before_quality = build_strategy_context_snapshot_quality_report(before)
    after_quality = build_strategy_context_snapshot_quality_report(after)
    added, removed, changed, changes = _observed_changes(before, after)
    blockers = _blockers(before, after, before_quality, after_quality)
    status = "OK" if not blockers else "BLOCKED"
    reason = (
        "strategy_context_snapshot_diff_ready"
        if status == "OK"
        else "strategy_context_snapshot_diff_blocked"
    )
    return StrategyContextSnapshotDiff(
        component="strategy_context_snapshot_diff",
        status=status,
        diff_mode="OBSERVATION_ONLY",
        diff_version="A23.v1",
        before_fingerprint=str(before.get("context_fingerprint", "")),
        after_fingerprint=str(after.get("context_fingerprint", "")),
        before_quality_status=str(before_quality["status"]),
        after_quality_status=str(after_quality["status"]),
        compared_fields=COMPARABLE_FIELDS,
        added_fields=added,
        removed_fields=removed,
        changed_fields=changed,
        changes=changes,
        safe_to_use_for_decision=False,
        decision_generated=False,
        proposal_generated=False,
        risk_approved=False,
        execution_allowed=False,
        safe_to_trade=False,
        real_trading=False,
        reason=reason,
        blockers=blockers,
        notes=(
            "A23 compares supplied snapshots in memory only.",
            "The diff is observational and never authorizes decisions, risk, proposals, or execution.",
        ),
    ).to_dict()


def _observed_changes(
    before: dict[str, object], after: dict[str, object]
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[dict[str, object], ...]]:
    added = tuple(field for field in COMPARABLE_FIELDS if field not in before and field in after)
    removed = tuple(field for field in COMPARABLE_FIELDS if field in before and field not in after)
    changed = tuple(
        field
        for field in COMPARABLE_FIELDS
        if field in before and field in after and before[field] != after[field]
    )
    changes = tuple(
        {"field": field, "before": before.get(field), "after": after.get(field)}
        for field in changed
    )
    return added, removed, changed, changes


def _blockers(
    before: dict[str, object],
    after: dict[str, object],
    before_quality: dict[str, object],
    after_quality: dict[str, object],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if before_quality["status"] != "OK":
        blockers.append("before_snapshot_quality_blocked")
    if after_quality["status"] != "OK":
        blockers.append("after_snapshot_quality_blocked")
    if any(before.get(flag) is not False or after.get(flag) is not False for flag in CRITICAL_FLAGS):
        blockers.append("critical_flags_not_blocked")
    return tuple(blockers)

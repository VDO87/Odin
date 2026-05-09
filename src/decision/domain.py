from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from shared.contracts import DecisionCycleResult, DecisionInputSnapshot, ExecutionIntent
from shared.enums import DecisionOutput, DecisionState, GlobalState
from shared.utils import ensure_utc, make_id, utc_now


@dataclass(frozen=True, slots=True)
class DecisionCandidate:
    hypothesis_id: str
    tactic_id: str
    instrument_id: str
    side: str
    score_value: float
    min_score_threshold: float
    reason_summary: str
    price_reference: float | None = None
    target_order_type: str = "MARKET"
    eligible: bool = True
    priority_base: int = 0
    confluence_quality_score: float = 0.0
    restriction_flags: tuple[str, ...] = tuple()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.hypothesis_id:
            raise ValueError("hypothesis_id is required")
        if not self.tactic_id:
            raise ValueError("tactic_id is required")
        if not self.instrument_id:
            raise ValueError("instrument_id is required")
        if not self.side:
            raise ValueError("side is required")
        if not self.reason_summary:
            raise ValueError("reason_summary is required")

    @property
    def is_viable(self) -> bool:
        return self.eligible and self.score_value >= self.min_score_threshold

    def to_audit_dict(self, *, ranking_position: int | None = None) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "tactic_id": self.tactic_id,
            "instrument_id": self.instrument_id,
            "side": self.side,
            "score_value": self.score_value,
            "min_score_threshold": self.min_score_threshold,
            "eligible": self.eligible,
            "is_viable": self.is_viable,
            "priority_base": self.priority_base,
            "confluence_quality_score": self.confluence_quality_score,
            "restriction_flags": list(self.restriction_flags),
            "reason_summary": self.reason_summary,
            "ranking_position": ranking_position,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class DecisionRationale:
    decision_cycle_id: str
    summary: str
    evaluated_candidates: tuple[dict[str, Any], ...]
    blocked_by_external: bool
    rationale_id: str = field(default_factory=lambda: make_id("rationale"))
    selected_hypothesis_id: str | None = None
    selected_tactic_id: str | None = None
    generated_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "generated_at_utc", ensure_utc(self.generated_at_utc))
        if not self.decision_cycle_id:
            raise ValueError("decision_cycle_id is required")
        if not self.summary:
            raise ValueError("summary is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rationale_id": self.rationale_id,
            "decision_cycle_id": self.decision_cycle_id,
            "selected_hypothesis_id": self.selected_hypothesis_id,
            "selected_tactic_id": self.selected_tactic_id,
            "summary": self.summary,
            "blocked_by_external": self.blocked_by_external,
            "evaluated_candidates": list(self.evaluated_candidates),
            "generated_at_utc": self.generated_at_utc.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class DecisionEvaluation:
    result: DecisionCycleResult
    rationale: DecisionRationale
    intent: ExecutionIntent | None = None


class DecisionEngine:
    def evaluate(
        self,
        snapshot: DecisionInputSnapshot,
        candidates: list[DecisionCandidate] | tuple[DecisionCandidate, ...],
        *,
        ttl_ms: int,
        max_slippage: float,
        decision_cycle_id: str | None = None,
        now_utc: datetime | None = None,
    ) -> DecisionEvaluation:
        if ttl_ms <= 0:
            raise ValueError("ttl_ms must be > 0")

        cycle_id = decision_cycle_id or make_id("decision-cycle")
        timestamp = ensure_utc(now_utc or utc_now())
        external_block_reason = self._external_block_reason(snapshot)
        ordered_candidates = sorted(candidates, key=self._ranking_key)
        audited_candidates = tuple(
            candidate.to_audit_dict(ranking_position=index)
            for index, candidate in enumerate(ordered_candidates, start=1)
        )

        if external_block_reason is not None:
            rationale = DecisionRationale(
                decision_cycle_id=cycle_id,
                summary=external_block_reason,
                evaluated_candidates=audited_candidates,
                blocked_by_external=True,
                generated_at_utc=timestamp,
            )
            result = DecisionCycleResult(
                decision_cycle_id=cycle_id,
                snapshot_id=snapshot.snapshot_id,
                decision_state=DecisionState.BLOCKED_EXTERNALLY,
                decision_output=DecisionOutput.BLOCKED,
                intent_emitted=False,
                blocked_by_external=True,
                reason_summary=external_block_reason,
                generated_at_utc=timestamp,
            )
            return DecisionEvaluation(result=result, rationale=rationale)

        viable_candidates = [candidate for candidate in ordered_candidates if candidate.is_viable]
        if not viable_candidates:
            output = DecisionOutput.NO_ACTION if not ordered_candidates else DecisionOutput.WAIT
            summary = "no_viable_candidate"
            rationale = DecisionRationale(
                decision_cycle_id=cycle_id,
                summary=summary,
                evaluated_candidates=audited_candidates,
                blocked_by_external=False,
                generated_at_utc=timestamp,
            )
            result = DecisionCycleResult(
                decision_cycle_id=cycle_id,
                snapshot_id=snapshot.snapshot_id,
                decision_state=DecisionState.NO_VALID_OPPORTUNITY,
                decision_output=output,
                intent_emitted=False,
                blocked_by_external=False,
                reason_summary=summary,
                generated_at_utc=timestamp,
            )
            return DecisionEvaluation(result=result, rationale=rationale)

        winner = viable_candidates[0]
        restriction_flags = self._restriction_flags(snapshot) + tuple(
            flag for flag in winner.restriction_flags if flag not in self._restriction_flags(snapshot)
        )
        output = DecisionOutput.RESTRICTED if restriction_flags else DecisionOutput.CANDIDATE_SELECTED
        summary = winner.reason_summary
        rationale = DecisionRationale(
            decision_cycle_id=cycle_id,
            summary=summary,
            evaluated_candidates=audited_candidates,
            blocked_by_external=False,
            rationale_id=make_id("rationale"),
            selected_hypothesis_id=winner.hypothesis_id,
            selected_tactic_id=winner.tactic_id,
            generated_at_utc=timestamp,
        )
        intent = ExecutionIntent.create(
            intent_id=make_id("intent"),
            decision_cycle_id=cycle_id,
            ttl_ms=ttl_ms,
            instrument_id=winner.instrument_id,
            side=winner.side,
            target_order_type=winner.target_order_type,
            max_slippage=max_slippage,
            market_snapshot_ref=snapshot.instrument_snapshot_ref,
            risk_snapshot_ref=f"risk-{snapshot.snapshot_id}",
            created_at_utc=timestamp,
            hypothesis_id=winner.hypothesis_id,
            tactic_id=winner.tactic_id,
            price_reference=winner.price_reference,
            decision_config_version=snapshot.decision_config_version,
            reason_summary=summary,
            intent_direction=winner.side,
            restriction_flags=restriction_flags,
            rationale_ref=rationale.rationale_id,
            memory_advisory_context_ref=snapshot.memory_advisory_context_ref,
        )
        result = DecisionCycleResult(
            decision_cycle_id=cycle_id,
            snapshot_id=snapshot.snapshot_id,
            decision_state=DecisionState.INTENT_EMITTED,
            decision_output=output,
            winner_hypothesis_id=winner.hypothesis_id,
            selected_tactic_id=winner.tactic_id,
            intent_id=intent.intent_id,
            intent_emitted=True,
            blocked_by_external=False,
            reason_summary=summary,
            generated_at_utc=timestamp,
        )
        return DecisionEvaluation(result=result, rationale=rationale, intent=intent)

    def _external_block_reason(self, snapshot: DecisionInputSnapshot) -> str | None:
        if snapshot.global_state not in {GlobalState.READY, GlobalState.MONITORING}:
            return "global_state_incompatible"
        if snapshot.kill_active:
            return "kill_active"
        if snapshot.active_block_vector_summary.get("active_block_count", 0) > 0:
            return "active_block_present"
        if snapshot.market_state in {"MS-30", "MS-40", "MS-50"}:
            return "market_incompatible"
        if snapshot.feed_integrity_state in {"FI-30", "FI-40"}:
            return "feed_integrity_incompatible"
        if snapshot.risk_state in {"BLOCK", "KILL", "RS-30", "RS-40"}:
            return "risk_blocks_execution"
        return None

    def _restriction_flags(self, snapshot: DecisionInputSnapshot) -> tuple[str, ...]:
        flags: list[str] = []
        if snapshot.market_state == "MS-20":
            flags.append("market_degraded")
        if snapshot.context_class == "MC-30":
            flags.append("context_sensitive")
        if snapshot.feed_integrity_state == "FI-20":
            flags.append("feed_degraded")
        if snapshot.risk_state in {"RESTRICT", "RS-20", "RS-50"}:
            flags.append("risk_restricted")
        return tuple(flags)

    def _ranking_key(self, candidate: DecisionCandidate) -> tuple[float, float, int, str]:
        return (
            -candidate.score_value,
            -candidate.confluence_quality_score,
            -candidate.priority_base,
            candidate.tactic_id,
        )

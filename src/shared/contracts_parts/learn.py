from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from shared.contracts_parts.core import CoreEventEnvelope
from shared.enums import (
    ApprovalMode,
    ApprovalStatus,
    EventType,
    LearnSnapshotType,
    LearnState,
    OperationalMode,
    PromotionResult,
    RollbackResult,
    Severity,
)
from shared.utils import ensure_utc, isoformat_utc, make_id, parse_datetime, utc_now


@dataclass(frozen=True, slots=True)
class LearningHistorySnapshot:
    time_window: dict[str, str]
    config_version_ref: str
    is_data_quality_sufficient: bool
    history_snapshot_id: str = field(default_factory=lambda: make_id("history-snapshot"))
    created_at_utc: datetime = field(default_factory=utc_now)
    decision_records_ref: str | None = None
    execution_records_ref: str | None = None
    risk_records_ref: str | None = None
    market_context_ref: str | None = None
    memory_advisory_refs: tuple[str, ...] = tuple()

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))
        if not self.time_window:
            raise ValueError("time_window is required")
        if not self.config_version_ref:
            raise ValueError("config_version_ref is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "history_snapshot_id": self.history_snapshot_id,
            "created_at_utc": isoformat_utc(self.created_at_utc),
            "time_window": dict(self.time_window),
            "decision_records_ref": self.decision_records_ref,
            "execution_records_ref": self.execution_records_ref,
            "risk_records_ref": self.risk_records_ref,
            "market_context_ref": self.market_context_ref,
            "config_version_ref": self.config_version_ref,
            "is_data_quality_sufficient": self.is_data_quality_sufficient,
            "memory_advisory_refs": list(self.memory_advisory_refs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningHistorySnapshot":
        return cls(
            history_snapshot_id=data["history_snapshot_id"],
            created_at_utc=parse_datetime(data["created_at_utc"]) or utc_now(),
            time_window=dict(data["time_window"]),
            decision_records_ref=data.get("decision_records_ref"),
            execution_records_ref=data.get("execution_records_ref"),
            risk_records_ref=data.get("risk_records_ref"),
            market_context_ref=data.get("market_context_ref"),
            config_version_ref=data["config_version_ref"],
            is_data_quality_sufficient=bool(data["is_data_quality_sufficient"]),
            memory_advisory_refs=tuple(data.get("memory_advisory_refs", [])),
        )


@dataclass(frozen=True, slots=True)
class ChangeProposal:
    source_analysis_id: str
    base_version_id: str
    candidate_version_id: str
    change_type: str
    changed_parameters: tuple[str, ...]
    old_values_ref: str
    new_values_ref: str
    reason_summary: str
    evidence_summary: str
    activation_mode: OperationalMode
    shadow_mode_required: bool
    proposal_id: str = field(default_factory=lambda: make_id("proposal"))
    created_at_utc: datetime = field(default_factory=utc_now)
    rollback_trigger_hints: tuple[str, ...] = tuple()
    memory_evidence_refs: tuple[str, ...] = tuple()

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))
        if not self.source_analysis_id:
            raise ValueError("source_analysis_id is required")
        if not self.base_version_id:
            raise ValueError("base_version_id is required")
        if not self.candidate_version_id:
            raise ValueError("candidate_version_id is required")
        if not self.change_type:
            raise ValueError("change_type is required")
        if not self.changed_parameters:
            raise ValueError("changed_parameters is required")
        if not self.old_values_ref:
            raise ValueError("old_values_ref is required")
        if not self.new_values_ref:
            raise ValueError("new_values_ref is required")
        if not self.reason_summary:
            raise ValueError("reason_summary is required")
        if not self.evidence_summary:
            raise ValueError("evidence_summary is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "created_at_utc": isoformat_utc(self.created_at_utc),
            "source_analysis_id": self.source_analysis_id,
            "base_version_id": self.base_version_id,
            "candidate_version_id": self.candidate_version_id,
            "change_type": self.change_type,
            "changed_parameters": list(self.changed_parameters),
            "old_values_ref": self.old_values_ref,
            "new_values_ref": self.new_values_ref,
            "reason_summary": self.reason_summary,
            "evidence_summary": self.evidence_summary,
            "activation_mode": self.activation_mode.value,
            "shadow_mode_required": self.shadow_mode_required,
            "rollback_trigger_hints": list(self.rollback_trigger_hints),
            "memory_evidence_refs": list(self.memory_evidence_refs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChangeProposal":
        return cls(
            proposal_id=data["proposal_id"],
            created_at_utc=parse_datetime(data["created_at_utc"]) or utc_now(),
            source_analysis_id=data["source_analysis_id"],
            base_version_id=data["base_version_id"],
            candidate_version_id=data["candidate_version_id"],
            change_type=data["change_type"],
            changed_parameters=tuple(data["changed_parameters"]),
            old_values_ref=data["old_values_ref"],
            new_values_ref=data["new_values_ref"],
            reason_summary=data["reason_summary"],
            evidence_summary=data["evidence_summary"],
            activation_mode=OperationalMode(data["activation_mode"]),
            shadow_mode_required=bool(data["shadow_mode_required"]),
            rollback_trigger_hints=tuple(data.get("rollback_trigger_hints", [])),
            memory_evidence_refs=tuple(data.get("memory_evidence_refs", [])),
        )


@dataclass(frozen=True, slots=True)
class VersionSnapshot:
    version_id: str
    snapshot_type: LearnSnapshotType
    config_ref: str
    is_recoverable: bool
    snapshot_id: str = field(default_factory=lambda: make_id("version-snapshot"))
    created_at_utc: datetime = field(default_factory=utc_now)
    weights_ref: str | None = None
    thresholds_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))
        if not self.version_id:
            raise ValueError("version_id is required")
        if not self.config_ref:
            raise ValueError("config_ref is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at_utc": isoformat_utc(self.created_at_utc),
            "version_id": self.version_id,
            "snapshot_type": self.snapshot_type.value,
            "config_ref": self.config_ref,
            "weights_ref": self.weights_ref,
            "thresholds_ref": self.thresholds_ref,
            "metadata": dict(self.metadata),
            "is_recoverable": self.is_recoverable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VersionSnapshot":
        return cls(
            snapshot_id=data["snapshot_id"],
            created_at_utc=parse_datetime(data["created_at_utc"]) or utc_now(),
            version_id=data["version_id"],
            snapshot_type=LearnSnapshotType(data["snapshot_type"]),
            config_ref=data["config_ref"],
            weights_ref=data.get("weights_ref"),
            thresholds_ref=data.get("thresholds_ref"),
            metadata=dict(data.get("metadata", {})),
            is_recoverable=bool(data["is_recoverable"]),
        )


@dataclass(frozen=True, slots=True)
class ApprovalState:
    proposal_id: str
    approval_mode: ApprovalMode
    approval_status: ApprovalStatus
    updated_at_utc: datetime = field(default_factory=utc_now)
    approved_by: str | None = None
    approved_at_utc: datetime | None = None
    approval_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "updated_at_utc", ensure_utc(self.updated_at_utc))
        if self.approved_at_utc is not None:
            object.__setattr__(self, "approved_at_utc", ensure_utc(self.approved_at_utc))
        if not self.proposal_id:
            raise ValueError("proposal_id is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "approval_mode": self.approval_mode.value,
            "approval_status": self.approval_status.value,
            "updated_at_utc": isoformat_utc(self.updated_at_utc),
            "approved_by": self.approved_by,
            "approved_at_utc": isoformat_utc(self.approved_at_utc) if self.approved_at_utc else None,
            "approval_reason": self.approval_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalState":
        return cls(
            proposal_id=data["proposal_id"],
            approval_mode=ApprovalMode(data["approval_mode"]),
            approval_status=ApprovalStatus(data["approval_status"]),
            updated_at_utc=parse_datetime(data["updated_at_utc"]) or utc_now(),
            approved_by=data.get("approved_by"),
            approved_at_utc=parse_datetime(data.get("approved_at_utc")),
            approval_reason=data.get("approval_reason"),
        )


@dataclass(frozen=True, slots=True)
class ShadowEvaluationSession:
    proposal_id: str
    candidate_version_id: str
    baseline_version_id: str
    evaluation_scope: str
    shadow_session_id: str = field(default_factory=lambda: make_id("shadow"))
    started_at_utc: datetime = field(default_factory=utc_now)
    ended_at_utc: datetime | None = None
    comparison_summary: str | None = None
    promotion_recommendation: PromotionResult | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "started_at_utc", ensure_utc(self.started_at_utc))
        if self.ended_at_utc is not None:
            object.__setattr__(self, "ended_at_utc", ensure_utc(self.ended_at_utc))
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if not self.candidate_version_id:
            raise ValueError("candidate_version_id is required")
        if not self.baseline_version_id:
            raise ValueError("baseline_version_id is required")
        if not self.evaluation_scope:
            raise ValueError("evaluation_scope is required")

    @property
    def is_completed(self) -> bool:
        return self.ended_at_utc is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "shadow_session_id": self.shadow_session_id,
            "proposal_id": self.proposal_id,
            "candidate_version_id": self.candidate_version_id,
            "baseline_version_id": self.baseline_version_id,
            "started_at_utc": isoformat_utc(self.started_at_utc),
            "ended_at_utc": isoformat_utc(self.ended_at_utc) if self.ended_at_utc else None,
            "evaluation_scope": self.evaluation_scope,
            "comparison_summary": self.comparison_summary,
            "promotion_recommendation": self.promotion_recommendation.value
            if self.promotion_recommendation
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShadowEvaluationSession":
        recommendation = data.get("promotion_recommendation")
        return cls(
            shadow_session_id=data["shadow_session_id"],
            proposal_id=data["proposal_id"],
            candidate_version_id=data["candidate_version_id"],
            baseline_version_id=data["baseline_version_id"],
            started_at_utc=parse_datetime(data["started_at_utc"]) or utc_now(),
            ended_at_utc=parse_datetime(data.get("ended_at_utc")),
            evaluation_scope=data["evaluation_scope"],
            comparison_summary=data.get("comparison_summary"),
            promotion_recommendation=PromotionResult(recommendation) if recommendation else None,
        )


@dataclass(frozen=True, slots=True)
class PromotionDecision:
    proposal_id: str
    candidate_version_id: str
    baseline_version_id: str
    promotion_result: PromotionResult
    reason_summary: str
    promotion_id: str = field(default_factory=lambda: make_id("promotion"))
    evaluated_at_utc: datetime = field(default_factory=utc_now)
    requires_restricted_activation: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "evaluated_at_utc", ensure_utc(self.evaluated_at_utc))
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if not self.candidate_version_id:
            raise ValueError("candidate_version_id is required")
        if not self.baseline_version_id:
            raise ValueError("baseline_version_id is required")
        if not self.reason_summary:
            raise ValueError("reason_summary is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "promotion_id": self.promotion_id,
            "proposal_id": self.proposal_id,
            "candidate_version_id": self.candidate_version_id,
            "baseline_version_id": self.baseline_version_id,
            "evaluated_at_utc": isoformat_utc(self.evaluated_at_utc),
            "promotion_result": self.promotion_result.value,
            "reason_summary": self.reason_summary,
            "requires_restricted_activation": self.requires_restricted_activation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromotionDecision":
        return cls(
            promotion_id=data["promotion_id"],
            proposal_id=data["proposal_id"],
            candidate_version_id=data["candidate_version_id"],
            baseline_version_id=data["baseline_version_id"],
            evaluated_at_utc=parse_datetime(data["evaluated_at_utc"]) or utc_now(),
            promotion_result=PromotionResult(data["promotion_result"]),
            reason_summary=data["reason_summary"],
            requires_restricted_activation=bool(data.get("requires_restricted_activation", False)),
        )


@dataclass(frozen=True, slots=True)
class VersionActivationRecord:
    version_id: str
    previous_version_id: str
    activation_mode: ApprovalMode
    restricted_post_activation: bool
    activation_id: str = field(default_factory=lambda: make_id("activation"))
    activated_at_utc: datetime = field(default_factory=utc_now)
    activated_by: str | None = None
    post_activation_monitoring_policy: str | None = None
    reason_summary: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "activated_at_utc", ensure_utc(self.activated_at_utc))
        if not self.version_id:
            raise ValueError("version_id is required")
        if not self.previous_version_id:
            raise ValueError("previous_version_id is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "activation_id": self.activation_id,
            "version_id": self.version_id,
            "previous_version_id": self.previous_version_id,
            "activated_at_utc": isoformat_utc(self.activated_at_utc),
            "activation_mode": self.activation_mode.value,
            "activated_by": self.activated_by,
            "restricted_post_activation": self.restricted_post_activation,
            "post_activation_monitoring_policy": self.post_activation_monitoring_policy,
            "reason_summary": self.reason_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VersionActivationRecord":
        return cls(
            activation_id=data["activation_id"],
            version_id=data["version_id"],
            previous_version_id=data["previous_version_id"],
            activated_at_utc=parse_datetime(data["activated_at_utc"]) or utc_now(),
            activation_mode=ApprovalMode(data["activation_mode"]),
            activated_by=data.get("activated_by"),
            restricted_post_activation=bool(data["restricted_post_activation"]),
            post_activation_monitoring_policy=data.get("post_activation_monitoring_policy"),
            reason_summary=data.get("reason_summary"),
        )

    @property
    def event_type(self) -> str:
        return EventType.LEARN_VERSION_ACTIVATED.value

    def to_core_payload(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "previous_version_id": self.previous_version_id,
            "activation_mode": self.activation_mode.value,
            "reason_summary": self.reason_summary,
            "restricted_post_activation": self.restricted_post_activation,
        }

    def to_core_event(self, source_module: str = "LEARN") -> CoreEventEnvelope:
        severity = Severity.WARN if self.restricted_post_activation else Severity.INFO
        return CoreEventEnvelope(
            event_type=self.event_type,
            source_module=source_module,
            severity=severity,
            payload=self.to_core_payload(),
        )


@dataclass(frozen=True, slots=True)
class RollbackRecord:
    from_version_id: str
    to_snapshot_id: str
    to_version_id: str
    rollback_reason: str
    rollback_result: RollbackResult
    rollback_id: str = field(default_factory=lambda: make_id("rollback"))
    triggered_at_utc: datetime = field(default_factory=utc_now)
    triggered_by: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "triggered_at_utc", ensure_utc(self.triggered_at_utc))
        if not self.from_version_id:
            raise ValueError("from_version_id is required")
        if not self.to_snapshot_id:
            raise ValueError("to_snapshot_id is required")
        if not self.to_version_id:
            raise ValueError("to_version_id is required")
        if not self.rollback_reason:
            raise ValueError("rollback_reason is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rollback_id": self.rollback_id,
            "triggered_at_utc": isoformat_utc(self.triggered_at_utc),
            "from_version_id": self.from_version_id,
            "to_snapshot_id": self.to_snapshot_id,
            "to_version_id": self.to_version_id,
            "rollback_reason": self.rollback_reason,
            "triggered_by": self.triggered_by,
            "rollback_result": self.rollback_result.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RollbackRecord":
        return cls(
            rollback_id=data["rollback_id"],
            triggered_at_utc=parse_datetime(data["triggered_at_utc"]) or utc_now(),
            from_version_id=data["from_version_id"],
            to_snapshot_id=data["to_snapshot_id"],
            to_version_id=data["to_version_id"],
            rollback_reason=data["rollback_reason"],
            triggered_by=data.get("triggered_by"),
            rollback_result=RollbackResult(data["rollback_result"]),
        )

    @property
    def event_type(self) -> str:
        if self.rollback_result == RollbackResult.COMPLETED:
            return EventType.LEARN_ROLLBACK.value
        if self.rollback_result == RollbackResult.BLOCKED:
            return EventType.LEARN_BLOCKED.value
        return EventType.LEARN_ERROR.value

    def to_core_payload(self) -> dict[str, Any]:
        return {
            "version_id": self.to_version_id,
            "previous_version_id": self.from_version_id,
            "reason_summary": self.rollback_reason,
            "rollback_result": self.rollback_result.value,
            "to_snapshot_id": self.to_snapshot_id,
        }

    def to_core_event(self, source_module: str = "LEARN") -> CoreEventEnvelope:
        severity = Severity.WARN
        if self.rollback_result == RollbackResult.FAILED:
            severity = Severity.ERROR
        return CoreEventEnvelope(
            event_type=self.event_type,
            source_module=source_module,
            severity=severity,
            payload=self.to_core_payload(),
        )


@dataclass(frozen=True, slots=True)
class LearnStateView:
    learn_state: LearnState
    updated_at_utc: datetime = field(default_factory=utc_now)
    active_version: str | None = None
    pending_proposal_id: str | None = None
    approval_status: ApprovalStatus | None = None
    rollback_state: RollbackResult | None = None
    last_change_summary: str | None = None
    shadow_required: bool = False
    shadow_session_id: str | None = None
    shadow_scope: str | None = None
    shadow_started_at_utc: datetime | None = None
    shadow_ended_at_utc: datetime | None = None
    shadow_promotion_recommendation: PromotionResult | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "updated_at_utc", ensure_utc(self.updated_at_utc))
        if self.shadow_started_at_utc is not None:
            object.__setattr__(self, "shadow_started_at_utc", ensure_utc(self.shadow_started_at_utc))
        if self.shadow_ended_at_utc is not None:
            object.__setattr__(self, "shadow_ended_at_utc", ensure_utc(self.shadow_ended_at_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "learn_state": self.learn_state.value,
            "updated_at_utc": isoformat_utc(self.updated_at_utc),
            "active_version": self.active_version,
            "pending_proposal_id": self.pending_proposal_id,
            "approval_status": self.approval_status.value if self.approval_status else None,
            "rollback_state": self.rollback_state.value if self.rollback_state else None,
            "last_change_summary": self.last_change_summary,
            "shadow_required": self.shadow_required,
            "shadow_session_id": self.shadow_session_id,
            "shadow_scope": self.shadow_scope,
            "shadow_started_at_utc": (
                isoformat_utc(self.shadow_started_at_utc) if self.shadow_started_at_utc else None
            ),
            "shadow_ended_at_utc": (
                isoformat_utc(self.shadow_ended_at_utc) if self.shadow_ended_at_utc else None
            ),
            "shadow_promotion_recommendation": self.shadow_promotion_recommendation.value
            if self.shadow_promotion_recommendation
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearnStateView":
        approval_status = data.get("approval_status")
        rollback_state = data.get("rollback_state")
        shadow_recommendation = data.get("shadow_promotion_recommendation")
        return cls(
            learn_state=LearnState(data["learn_state"]),
            updated_at_utc=parse_datetime(data["updated_at_utc"]) or utc_now(),
            active_version=data.get("active_version"),
            pending_proposal_id=data.get("pending_proposal_id"),
            approval_status=ApprovalStatus(approval_status) if approval_status else None,
            rollback_state=RollbackResult(rollback_state) if rollback_state else None,
            last_change_summary=data.get("last_change_summary"),
            shadow_required=bool(data.get("shadow_required", False)),
            shadow_session_id=data.get("shadow_session_id"),
            shadow_scope=data.get("shadow_scope"),
            shadow_started_at_utc=parse_datetime(data.get("shadow_started_at_utc")),
            shadow_ended_at_utc=parse_datetime(data.get("shadow_ended_at_utc")),
            shadow_promotion_recommendation=PromotionResult(shadow_recommendation)
            if shadow_recommendation
            else None,
        )

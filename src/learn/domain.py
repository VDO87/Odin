from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from persistence.state_store import PersistentStateStore
from shared.contracts import (
    ApprovalState,
    ChangeProposal,
    CoreEventEnvelope,
    LearnStateView,
    LearningHistorySnapshot,
    PromotionDecision,
    RollbackRecord,
    ShadowEvaluationSession,
    VersionActivationRecord,
    VersionSnapshot,
)
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
from shared.utils import utc_now


@dataclass(frozen=True, slots=True)
class LearningActivationEvaluation:
    accepted: bool
    promotion_decision: PromotionDecision
    activation_record: VersionActivationRecord | None = None
    blocking_reason_code: str | None = None
    blocking_summary: str | None = None

    def to_core_event(self) -> CoreEventEnvelope:
        if self.activation_record is not None:
            return self.activation_record.to_core_event()
        return CoreEventEnvelope(
            event_type=EventType.LEARN_BLOCKED.value,
            source_module="LEARN",
            severity=Severity.WARN,
            payload={
                "version_id": self.promotion_decision.candidate_version_id,
                "previous_version_id": self.promotion_decision.baseline_version_id,
                "reason_summary": self.blocking_summary or self.promotion_decision.reason_summary,
                "blocking_reason_code": self.blocking_reason_code,
                "promotion_result": self.promotion_decision.promotion_result.value,
            },
        )


@dataclass(frozen=True, slots=True)
class LearningRollbackEvaluation:
    accepted: bool
    rollback_record: RollbackRecord | None = None
    restored_activation: VersionActivationRecord | None = None
    blocking_reason_code: str | None = None
    blocking_summary: str | None = None

    def to_core_event(self) -> CoreEventEnvelope:
        if self.rollback_record is not None:
            return self.rollback_record.to_core_event()
        return CoreEventEnvelope(
            event_type=EventType.LEARN_BLOCKED.value,
            source_module="LEARN",
            severity=Severity.WARN,
            payload={
                "reason_summary": self.blocking_summary,
                "blocking_reason_code": self.blocking_reason_code,
            },
        )


class LearningOrchestrator:
    def __init__(self, store: PersistentStateStore) -> None:
        self._store = store

    def create_history_snapshot(
        self,
        *,
        time_window: dict[str, str],
        config_version_ref: str,
        is_data_quality_sufficient: bool,
        decision_records_ref: str | None = None,
        execution_records_ref: str | None = None,
        risk_records_ref: str | None = None,
        market_context_ref: str | None = None,
        memory_advisory_refs: tuple[str, ...] = tuple(),
    ) -> LearningHistorySnapshot:
        snapshot = LearningHistorySnapshot(
            time_window=time_window,
            decision_records_ref=decision_records_ref,
            execution_records_ref=execution_records_ref,
            risk_records_ref=risk_records_ref,
            market_context_ref=market_context_ref,
            config_version_ref=config_version_ref,
            is_data_quality_sufficient=is_data_quality_sufficient,
            memory_advisory_refs=memory_advisory_refs,
        )
        self._store.write_learning_history_snapshot(snapshot)
        return snapshot

    def create_change_proposal(
        self,
        *,
        source_analysis_id: str,
        base_version_id: str,
        candidate_version_id: str,
        change_type: str,
        changed_parameters: tuple[str, ...],
        old_values_ref: str,
        new_values_ref: str,
        reason_summary: str,
        evidence_summary: str,
        activation_mode: OperationalMode,
        shadow_mode_required: bool,
        rollback_trigger_hints: tuple[str, ...] = tuple(),
        memory_evidence_refs: tuple[str, ...] = tuple(),
    ) -> ChangeProposal:
        proposal = ChangeProposal(
            source_analysis_id=source_analysis_id,
            base_version_id=base_version_id,
            candidate_version_id=candidate_version_id,
            change_type=change_type,
            changed_parameters=changed_parameters,
            old_values_ref=old_values_ref,
            new_values_ref=new_values_ref,
            reason_summary=reason_summary,
            evidence_summary=evidence_summary,
            activation_mode=activation_mode,
            shadow_mode_required=shadow_mode_required,
            rollback_trigger_hints=rollback_trigger_hints,
            memory_evidence_refs=memory_evidence_refs,
        )
        self._store.write_change_proposal(proposal)
        return proposal

    def create_version_snapshot(
        self,
        *,
        version_id: str,
        snapshot_type: LearnSnapshotType,
        config_ref: str,
        is_recoverable: bool,
        weights_ref: str | None = None,
        thresholds_ref: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> VersionSnapshot:
        snapshot = VersionSnapshot(
            version_id=version_id,
            snapshot_type=snapshot_type,
            config_ref=config_ref,
            weights_ref=weights_ref,
            thresholds_ref=thresholds_ref,
            metadata=dict(metadata or {}),
            is_recoverable=is_recoverable,
        )
        self._store.write_version_snapshot(snapshot)
        return snapshot

    def record_approval(
        self,
        *,
        proposal_id: str,
        approval_mode: ApprovalMode,
        approval_status: ApprovalStatus,
        approval_reason: str | None = None,
        approved_by: str | None = None,
    ) -> ApprovalState:
        self._require_proposal(proposal_id)
        approved_at_utc = utc_now() if approval_status == ApprovalStatus.APPROVED else None
        approval = ApprovalState(
            proposal_id=proposal_id,
            approval_mode=approval_mode,
            approval_status=approval_status,
            approved_by=approved_by,
            approved_at_utc=approved_at_utc,
            approval_reason=approval_reason,
        )
        self._store.write_approval_state(approval)
        return approval

    def start_shadow_session(
        self,
        *,
        proposal_id: str,
        evaluation_scope: str,
    ) -> ShadowEvaluationSession:
        proposal = self._require_proposal(proposal_id)
        session = ShadowEvaluationSession(
            proposal_id=proposal.proposal_id,
            candidate_version_id=proposal.candidate_version_id,
            baseline_version_id=proposal.base_version_id,
            evaluation_scope=evaluation_scope,
        )
        self._store.write_shadow_session(session)
        return session

    def complete_shadow_session(
        self,
        *,
        proposal_id: str,
        comparison_summary: str,
        promotion_recommendation: PromotionResult,
    ) -> ShadowEvaluationSession:
        session = self._store.read_latest_shadow_session_for_proposal(proposal_id)
        if session is None:
            raise ValueError("shadow session not found for proposal")
        completed = ShadowEvaluationSession(
            shadow_session_id=session.shadow_session_id,
            proposal_id=session.proposal_id,
            candidate_version_id=session.candidate_version_id,
            baseline_version_id=session.baseline_version_id,
            started_at_utc=session.started_at_utc,
            ended_at_utc=utc_now(),
            evaluation_scope=session.evaluation_scope,
            comparison_summary=comparison_summary,
            promotion_recommendation=promotion_recommendation,
        )
        self._store.write_shadow_session(completed)
        return completed

    def evaluate_promotion(
        self,
        *,
        proposal_id: str,
        activation_allowed: bool = True,
        risk_state_compatible: bool = True,
        requires_restricted_activation: bool = False,
    ) -> PromotionDecision:
        proposal = self._require_proposal(proposal_id)
        approval = self._store.read_approval_state(proposal_id)
        pre_activation_snapshot = self._store.read_latest_version_snapshot_for_version(
            proposal.base_version_id,
            snapshot_type=LearnSnapshotType.PRE_ACTIVATION,
            recoverable_only=True,
        )
        shadow_session = self._store.read_latest_shadow_session_for_proposal(proposal_id)

        result = (
            PromotionResult.PROMOTE_RESTRICTED
            if requires_restricted_activation
            else PromotionResult.PROMOTE
        )
        reason_summary = "promotion_allowed"

        if approval is None or approval.approval_status == ApprovalStatus.PENDING:
            result = PromotionResult.HOLD
            reason_summary = "approval_pending"
        elif approval.approval_status in {ApprovalStatus.REJECTED, ApprovalStatus.BLOCKED}:
            result = PromotionResult.REJECT
            reason_summary = "approval_rejected_or_blocked"
        elif pre_activation_snapshot is None:
            result = PromotionResult.HOLD
            reason_summary = "missing_pre_activation_snapshot"
        elif self._requires_shadow(proposal, approval) and (
            shadow_session is None or not shadow_session.is_completed
        ):
            result = PromotionResult.HOLD
            reason_summary = "shadow_session_required"
        elif (
            shadow_session
            and shadow_session.promotion_recommendation == PromotionResult.ROLLBACK_REQUIRED
        ):
            result = PromotionResult.ROLLBACK_REQUIRED
            reason_summary = "shadow_requires_rollback"
        elif shadow_session and shadow_session.promotion_recommendation == PromotionResult.REJECT:
            result = PromotionResult.REJECT
            reason_summary = "shadow_rejected_candidate"
        elif not activation_allowed:
            result = PromotionResult.HOLD
            reason_summary = "core_activation_not_allowed"
        elif not risk_state_compatible:
            result = PromotionResult.HOLD
            reason_summary = "risk_context_incompatible"
        elif (
            shadow_session
            and shadow_session.promotion_recommendation == PromotionResult.PROMOTE_RESTRICTED
        ):
            result = PromotionResult.PROMOTE_RESTRICTED
            reason_summary = "shadow_recommends_restricted_promotion"

        decision = PromotionDecision(
            proposal_id=proposal.proposal_id,
            candidate_version_id=proposal.candidate_version_id,
            baseline_version_id=proposal.base_version_id,
            promotion_result=result,
            reason_summary=reason_summary,
            requires_restricted_activation=result == PromotionResult.PROMOTE_RESTRICTED,
        )
        self._store.write_promotion_decision(decision)
        return decision

    def activate_proposal(
        self,
        *,
        proposal_id: str,
        activated_by: str | None = None,
        post_activation_monitoring_policy: str | None = None,
        activation_allowed: bool = True,
        risk_state_compatible: bool = True,
        requires_restricted_activation: bool = False,
    ) -> LearningActivationEvaluation:
        proposal = self._require_proposal(proposal_id)
        approval = self._require_approval(proposal_id)
        decision = self.evaluate_promotion(
            proposal_id=proposal_id,
            activation_allowed=activation_allowed,
            risk_state_compatible=risk_state_compatible,
            requires_restricted_activation=requires_restricted_activation,
        )

        if decision.promotion_result not in {
            PromotionResult.PROMOTE,
            PromotionResult.PROMOTE_RESTRICTED,
        }:
            return LearningActivationEvaluation(
                accepted=False,
                promotion_decision=decision,
                blocking_reason_code=decision.reason_summary,
                blocking_summary=decision.reason_summary,
            )

        activation = VersionActivationRecord(
            version_id=proposal.candidate_version_id,
            previous_version_id=proposal.base_version_id,
            activation_mode=approval.approval_mode,
            activated_by=activated_by,
            restricted_post_activation=decision.requires_restricted_activation,
            post_activation_monitoring_policy=post_activation_monitoring_policy,
            reason_summary=proposal.reason_summary,
        )
        self._store.write_version_activation(activation)

        active_baseline = VersionSnapshot(
            version_id=proposal.candidate_version_id,
            snapshot_type=LearnSnapshotType.ACTIVE_BASELINE,
            config_ref=proposal.new_values_ref,
            is_recoverable=True,
            metadata={
                "proposal_id": proposal.proposal_id,
                "promotion_id": decision.promotion_id,
            },
        )
        self._store.write_version_snapshot(active_baseline)

        return LearningActivationEvaluation(
            accepted=True,
            promotion_decision=decision,
            activation_record=activation,
        )

    def rollback_active_version(
        self,
        *,
        rollback_reason: str,
        triggered_by: str | None = None,
    ) -> LearningRollbackEvaluation:
        latest_activation = self._store.read_latest_version_activation()
        if latest_activation is None:
            return LearningRollbackEvaluation(
                accepted=False,
                blocking_reason_code="missing_active_version",
                blocking_summary="missing_active_version",
            )

        current_snapshot = self._store.read_latest_version_snapshot_for_version(
            latest_activation.version_id,
            recoverable_only=True,
        )
        target_snapshot = self._store.read_latest_version_snapshot_for_version(
            latest_activation.previous_version_id,
            recoverable_only=True,
        )
        if target_snapshot is None:
            return LearningRollbackEvaluation(
                accepted=False,
                blocking_reason_code="missing_recoverable_snapshot",
                blocking_summary="missing_recoverable_snapshot",
            )

        rollback_target = VersionSnapshot(
            version_id=latest_activation.version_id,
            snapshot_type=LearnSnapshotType.ROLLBACK_TARGET,
            config_ref=(
                current_snapshot.config_ref
                if current_snapshot
                else latest_activation.version_id
            ),
            weights_ref=current_snapshot.weights_ref if current_snapshot else None,
            thresholds_ref=current_snapshot.thresholds_ref if current_snapshot else None,
            metadata={
                "rollback_reason": rollback_reason,
                "replaced_by_version_id": latest_activation.previous_version_id,
            },
            is_recoverable=True,
        )
        self._store.write_version_snapshot(rollback_target)

        rollback = RollbackRecord(
            from_version_id=latest_activation.version_id,
            to_snapshot_id=target_snapshot.snapshot_id,
            to_version_id=latest_activation.previous_version_id,
            rollback_reason=rollback_reason,
            triggered_by=triggered_by,
            rollback_result=RollbackResult.COMPLETED,
        )
        self._store.write_rollback_record(rollback)

        restored_activation = VersionActivationRecord(
            version_id=latest_activation.previous_version_id,
            previous_version_id=latest_activation.version_id,
            activation_mode=ApprovalMode.MANUAL,
            activated_by=triggered_by,
            restricted_post_activation=True,
            post_activation_monitoring_policy="rollback_reinforced_observation",
            reason_summary=f"rollback::{rollback_reason}",
        )
        self._store.write_version_activation(restored_activation)

        restored_baseline = VersionSnapshot(
            version_id=latest_activation.previous_version_id,
            snapshot_type=LearnSnapshotType.ACTIVE_BASELINE,
            config_ref=target_snapshot.config_ref,
            weights_ref=target_snapshot.weights_ref,
            thresholds_ref=target_snapshot.thresholds_ref,
            metadata={
                "rollback_id": rollback.rollback_id,
                "from_version_id": latest_activation.version_id,
            },
            is_recoverable=True,
        )
        self._store.write_version_snapshot(restored_baseline)

        return LearningRollbackEvaluation(
            accepted=True,
            rollback_record=rollback,
            restored_activation=restored_activation,
        )

    def read_change_proposal(self, *, proposal_id: str) -> ChangeProposal | None:
        return self._store.read_change_proposal(proposal_id)

    def read_latest_change_proposal(self) -> ChangeProposal | None:
        return self._store.read_latest_change_proposal()

    def list_change_proposals(
        self,
        *,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[ChangeProposal, ...]:
        return self._store.list_change_proposals(
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

    def read_approval_state(self, *, proposal_id: str) -> ApprovalState | None:
        return self._store.read_approval_state(proposal_id)

    def list_approval_states(
        self,
        *,
        proposal_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[ApprovalState, ...]:
        return self._store.list_approval_states(
            proposal_id=proposal_id,
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

    def read_latest_shadow_session_for_proposal(
        self,
        *,
        proposal_id: str,
    ) -> ShadowEvaluationSession | None:
        return self._store.read_latest_shadow_session_for_proposal(proposal_id)

    def list_shadow_sessions(
        self,
        *,
        proposal_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[ShadowEvaluationSession, ...]:
        return self._store.list_shadow_sessions(
            proposal_id=proposal_id,
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

    def read_latest_promotion_decision(
        self,
        *,
        proposal_id: str | None = None,
    ) -> PromotionDecision | None:
        return self._store.read_latest_promotion_decision(proposal_id=proposal_id)

    def list_promotion_decisions(
        self,
        *,
        proposal_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[PromotionDecision, ...]:
        return self._store.list_promotion_decisions(
            proposal_id=proposal_id,
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

    def read_latest_version_activation(self) -> VersionActivationRecord | None:
        return self._store.read_latest_version_activation()

    def read_latest_rollback_record(self) -> RollbackRecord | None:
        return self._store.read_latest_rollback_record()

    def list_rollback_records(
        self,
        *,
        version_id: str | None = None,
        start_at_utc: datetime | None = None,
        end_at_utc: datetime | None = None,
    ) -> tuple[RollbackRecord, ...]:
        return self._store.list_rollback_records(
            version_id=version_id,
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

    def read_state_view(self) -> LearnStateView:
        latest_proposal = self.read_latest_change_proposal()
        latest_activation = self.read_latest_version_activation()
        latest_rollback = self.read_latest_rollback_record()

        learn_state = LearnState.INACTIVE
        pending_proposal_id: str | None = None
        approval_status: ApprovalStatus | None = None
        shadow_required = False
        shadow_session: ShadowEvaluationSession | None = None
        last_change_summary: str | None = None

        if latest_proposal is not None:
            approval = self.read_approval_state(proposal_id=latest_proposal.proposal_id)
            approval_status = approval.approval_status if approval else None
            pending_proposal_id = latest_proposal.proposal_id
            learn_state = LearnState.PROPOSAL_GENERATED
            shadow_required = self._requires_shadow(latest_proposal, approval)
            shadow_session = self.read_latest_shadow_session_for_proposal(
                proposal_id=latest_proposal.proposal_id
            )
            last_change_summary = latest_proposal.reason_summary
            if approval_status == ApprovalStatus.PENDING:
                learn_state = LearnState.WAITING_APPROVAL
            elif shadow_required:
                if shadow_session is not None and not shadow_session.is_completed:
                    learn_state = LearnState.SHADOW_RUNNING

        if latest_activation is not None:
            learn_state = LearnState.VERSION_ACTIVE_MONITORING
            pending_proposal_id = None
            last_change_summary = latest_activation.reason_summary or last_change_summary
        if (
            latest_rollback is not None
            and latest_rollback.rollback_result == RollbackResult.COMPLETED
        ):
            learn_state = LearnState.ROLLED_BACK
            last_change_summary = latest_rollback.rollback_reason or last_change_summary

        return LearnStateView(
            learn_state=learn_state,
            active_version=latest_activation.version_id if latest_activation else None,
            pending_proposal_id=pending_proposal_id,
            approval_status=approval_status,
            rollback_state=latest_rollback.rollback_result if latest_rollback else None,
            last_change_summary=last_change_summary,
            shadow_required=shadow_required,
            shadow_session_id=shadow_session.shadow_session_id if shadow_session else None,
            shadow_scope=shadow_session.evaluation_scope if shadow_session else None,
            shadow_started_at_utc=shadow_session.started_at_utc if shadow_session else None,
            shadow_ended_at_utc=shadow_session.ended_at_utc if shadow_session else None,
            shadow_promotion_recommendation=(
                shadow_session.promotion_recommendation if shadow_session else None
            ),
        )

    def _require_proposal(self, proposal_id: str) -> ChangeProposal:
        proposal = self._store.read_change_proposal(proposal_id)
        if proposal is None:
            raise ValueError(f"proposal not found: {proposal_id}")
        return proposal

    def _require_approval(self, proposal_id: str) -> ApprovalState:
        approval = self._store.read_approval_state(proposal_id)
        if approval is None:
            raise ValueError(f"approval not found for proposal: {proposal_id}")
        return approval

    def _requires_shadow(
        self,
        proposal: ChangeProposal,
        approval: ApprovalState | None,
    ) -> bool:
        return proposal.shadow_mode_required or (
            approval is not None and approval.approval_mode == ApprovalMode.SHADOW_THEN_APPROVE
        )

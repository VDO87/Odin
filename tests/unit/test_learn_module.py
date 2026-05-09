from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from learn import (
    ApprovalState,
    ApprovalMode,
    ApprovalStatus,
    ChangeProposal,
    LearnSnapshotType,
    LearningOrchestrator,
    PromotionDecision,
    PromotionResult,
    RollbackRecord,
    RollbackResult,
    ShadowEvaluationSession,
    VersionActivationRecord,
)
from persistence.sqlite_state_store import SQLiteStateStore
from shared.enums import LearnState, OperationalMode


def build_orchestrator(tmp_path: Path) -> tuple[SQLiteStateStore, LearningOrchestrator]:
    store = SQLiteStateStore(tmp_path / "state" / "core_state.db")
    store.initialize()
    return store, LearningOrchestrator(store)


def test_learning_history_snapshot_is_persisted_and_readable(tmp_path: Path) -> None:
    store, orchestrator = build_orchestrator(tmp_path)

    snapshot = orchestrator.create_history_snapshot(
        time_window={
            "start_at_utc": "2026-04-01T00:00:00+00:00",
            "end_at_utc": "2026-04-09T00:00:00+00:00",
        },
        config_version_ref="cfg-v1",
        is_data_quality_sufficient=True,
        decision_records_ref="decision-batch-1",
        execution_records_ref="exec-batch-1",
        risk_records_ref="risk-batch-1",
    )
    restored = store.read_latest_learning_history_snapshot()

    assert restored is not None
    assert restored.history_snapshot_id == snapshot.history_snapshot_id
    assert restored.config_version_ref == "cfg-v1"
    assert restored.is_data_quality_sufficient is True


def test_activation_requires_shadow_when_proposal_demands_it(tmp_path: Path) -> None:
    _, orchestrator = build_orchestrator(tmp_path)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-1",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="threshold_adjustment",
        changed_parameters=("entry_threshold",),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate improves selective entry quality",
        evidence_summary="positive delta across stable windows",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=True,
    )
    orchestrator.create_version_snapshot(
        version_id="decision-v1",
        snapshot_type=LearnSnapshotType.PRE_ACTIVATION,
        config_ref="cfg://decision-v1",
        is_recoverable=True,
    )
    orchestrator.record_approval(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.SHADOW_THEN_APPROVE,
        approval_status=ApprovalStatus.APPROVED,
        approved_by="ops-supervisor",
    )

    evaluation = orchestrator.activate_proposal(proposal_id=proposal.proposal_id)

    assert evaluation.accepted is False
    assert evaluation.blocking_reason_code == "shadow_session_required"
    assert evaluation.blocking_summary == "shadow_session_required"
    assert evaluation.promotion_decision.promotion_result == PromotionResult.HOLD
    assert evaluation.to_core_event().event_type == "EV-LEARN-BLOCKED"


def test_activation_is_blocked_when_approval_is_pending(tmp_path: Path) -> None:
    _, orchestrator = build_orchestrator(tmp_path)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-pending-approval",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="threshold_adjustment",
        changed_parameters=("entry_threshold",),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate still awaits review",
        evidence_summary="review not completed",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=False,
    )
    orchestrator.create_version_snapshot(
        version_id="decision-v1",
        snapshot_type=LearnSnapshotType.PRE_ACTIVATION,
        config_ref="cfg://decision-v1",
        is_recoverable=True,
    )
    orchestrator.record_approval(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.MANUAL,
        approval_status=ApprovalStatus.PENDING,
        approval_reason="awaiting review",
    )

    evaluation = orchestrator.activate_proposal(proposal_id=proposal.proposal_id)

    assert evaluation.accepted is False
    assert evaluation.blocking_reason_code == "approval_pending"
    assert evaluation.blocking_summary == "approval_pending"
    assert evaluation.promotion_decision.promotion_result == PromotionResult.HOLD


def test_activation_is_blocked_when_approval_is_rejected_or_blocked(tmp_path: Path) -> None:
    _, orchestrator = build_orchestrator(tmp_path)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-rejected-approval",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="threshold_adjustment",
        changed_parameters=("entry_threshold",),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate failed governance review",
        evidence_summary="review rejected the change",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=False,
    )
    orchestrator.create_version_snapshot(
        version_id="decision-v1",
        snapshot_type=LearnSnapshotType.PRE_ACTIVATION,
        config_ref="cfg://decision-v1",
        is_recoverable=True,
    )
    orchestrator.record_approval(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.MANUAL,
        approval_status=ApprovalStatus.REJECTED,
        approval_reason="rejected after review",
    )

    evaluation = orchestrator.activate_proposal(proposal_id=proposal.proposal_id)

    assert evaluation.accepted is False
    assert evaluation.blocking_reason_code == "approval_rejected_or_blocked"
    assert evaluation.blocking_summary == "approval_rejected_or_blocked"
    assert evaluation.promotion_decision.promotion_result == PromotionResult.REJECT


def test_activation_persists_active_version_and_state_view(tmp_path: Path) -> None:
    store, orchestrator = build_orchestrator(tmp_path)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-2",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="weight_adjustment",
        changed_parameters=("weight_momentum", "weight_volatility"),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate improves reward to risk profile",
        evidence_summary="stable uplift in replay and demo batches",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=False,
    )
    orchestrator.create_version_snapshot(
        version_id="decision-v1",
        snapshot_type=LearnSnapshotType.PRE_ACTIVATION,
        config_ref="cfg://decision-v1",
        is_recoverable=True,
    )
    orchestrator.record_approval(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.MANUAL,
        approval_status=ApprovalStatus.APPROVED,
        approved_by="ops-supervisor",
    )

    evaluation = orchestrator.activate_proposal(
        proposal_id=proposal.proposal_id,
        activated_by="ops-supervisor",
        post_activation_monitoring_policy="monitor-4h",
    )
    restored_activation = store.read_latest_version_activation()
    active_baseline = store.read_latest_version_snapshot_for_version(
        "decision-v2",
        snapshot_type=LearnSnapshotType.ACTIVE_BASELINE,
        recoverable_only=True,
    )
    state_view = orchestrator.read_state_view()

    assert evaluation.accepted is True
    assert restored_activation is not None
    assert restored_activation.version_id == "decision-v2"
    assert evaluation.to_core_event().event_type == "EV-LEARN-VERSION-ACTIVATED"
    assert active_baseline is not None
    assert active_baseline.config_ref == "cfg://decision-v2"
    assert state_view.learn_state == LearnState.VERSION_ACTIVE_MONITORING
    assert state_view.active_version == "decision-v2"


def test_rollback_restores_previous_version_and_persists_audit_records(tmp_path: Path) -> None:
    store, orchestrator = build_orchestrator(tmp_path)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-3",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="config_bundle",
        changed_parameters=("entry_threshold", "stop_loss_multiplier"),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate broadens opportunity coverage",
        evidence_summary="improved replay utilization before degradation",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=False,
    )
    orchestrator.create_version_snapshot(
        version_id="decision-v1",
        snapshot_type=LearnSnapshotType.PRE_ACTIVATION,
        config_ref="cfg://decision-v1",
        is_recoverable=True,
    )
    orchestrator.record_approval(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.MANUAL,
        approval_status=ApprovalStatus.APPROVED,
        approved_by="ops-supervisor",
    )
    activation = orchestrator.activate_proposal(proposal_id=proposal.proposal_id)

    rollback = orchestrator.rollback_active_version(
        rollback_reason="post_activation_degradation_detected",
        triggered_by="ops-supervisor",
    )
    restored_activation = store.read_latest_version_activation()
    rollback_record = store.read_latest_rollback_record()
    rollback_target = store.read_latest_version_snapshot_for_version(
        "decision-v2",
        snapshot_type=LearnSnapshotType.ROLLBACK_TARGET,
        recoverable_only=True,
    )

    assert activation.accepted is True
    assert rollback.accepted is True
    assert rollback_record is not None
    assert rollback_record.to_version_id == "decision-v1"
    assert rollback.to_core_event().event_type == "EV-LEARN-ROLLBACK"
    assert restored_activation is not None
    assert restored_activation.version_id == "decision-v1"
    assert rollback_target is not None


def test_activation_is_blocked_when_shadow_rejects_candidate(tmp_path: Path) -> None:
    _, orchestrator = build_orchestrator(tmp_path)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-shadow-reject",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="risk_guard_adjustment",
        changed_parameters=("stop_loss_multiplier",),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate needs completed shadow review",
        evidence_summary="shadow later rejected the candidate",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=True,
    )
    orchestrator.create_version_snapshot(
        version_id="decision-v1",
        snapshot_type=LearnSnapshotType.PRE_ACTIVATION,
        config_ref="cfg://decision-v1",
        is_recoverable=True,
    )
    orchestrator.record_approval(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.SHADOW_THEN_APPROVE,
        approval_status=ApprovalStatus.APPROVED,
        approved_by="ops-supervisor",
    )
    orchestrator.start_shadow_session(
        proposal_id=proposal.proposal_id,
        evaluation_scope="shadow-24h",
    )
    orchestrator.complete_shadow_session(
        proposal_id=proposal.proposal_id,
        comparison_summary="candidate underperformed the baseline",
        promotion_recommendation=PromotionResult.REJECT,
    )

    evaluation = orchestrator.activate_proposal(proposal_id=proposal.proposal_id)

    assert evaluation.accepted is False
    assert evaluation.blocking_reason_code == "shadow_rejected_candidate"
    assert evaluation.blocking_summary == "shadow_rejected_candidate"
    assert evaluation.promotion_decision.promotion_result == PromotionResult.REJECT


def test_activation_is_blocked_when_shadow_requires_rollback(tmp_path: Path) -> None:
    _, orchestrator = build_orchestrator(tmp_path)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-shadow-rollback",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="policy_shift",
        changed_parameters=("entry_threshold", "stop_loss_multiplier"),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate completed shadow with rollback recommendation",
        evidence_summary="shadow identified unsafe degradation",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=True,
    )
    orchestrator.create_version_snapshot(
        version_id="decision-v1",
        snapshot_type=LearnSnapshotType.PRE_ACTIVATION,
        config_ref="cfg://decision-v1",
        is_recoverable=True,
    )
    orchestrator.record_approval(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.SHADOW_THEN_APPROVE,
        approval_status=ApprovalStatus.APPROVED,
        approved_by="ops-supervisor",
    )
    orchestrator.start_shadow_session(
        proposal_id=proposal.proposal_id,
        evaluation_scope="shadow-24h",
    )
    orchestrator.complete_shadow_session(
        proposal_id=proposal.proposal_id,
        comparison_summary="candidate triggered rollback conditions",
        promotion_recommendation=PromotionResult.ROLLBACK_REQUIRED,
    )

    evaluation = orchestrator.activate_proposal(proposal_id=proposal.proposal_id)

    assert evaluation.accepted is False
    assert evaluation.blocking_reason_code == "shadow_requires_rollback"
    assert evaluation.blocking_summary == "shadow_requires_rollback"
    assert evaluation.promotion_decision.promotion_result == PromotionResult.ROLLBACK_REQUIRED


def test_rollback_is_blocked_without_active_version(tmp_path: Path) -> None:
    _, orchestrator = build_orchestrator(tmp_path)

    rollback = orchestrator.rollback_active_version(
        rollback_reason="no active version present",
        triggered_by="ops-supervisor",
    )

    assert rollback.accepted is False
    assert rollback.blocking_reason_code == "missing_active_version"
    assert rollback.blocking_summary == "missing_active_version"
    assert rollback.rollback_record is None


def test_rollback_is_blocked_without_recoverable_snapshot(tmp_path: Path) -> None:
    store, orchestrator = build_orchestrator(tmp_path)

    store.write_version_activation(
        activation=VersionActivationRecord(
            version_id="decision-v2",
            previous_version_id="decision-v1",
            activation_mode=ApprovalMode.MANUAL,
            restricted_post_activation=False,
            activated_by="ops-supervisor",
        ),
    )

    rollback = orchestrator.rollback_active_version(
        rollback_reason="missing rollback target snapshot",
        triggered_by="ops-supervisor",
    )

    assert rollback.accepted is False
    assert rollback.blocking_reason_code == "missing_recoverable_snapshot"
    assert rollback.blocking_summary == "missing_recoverable_snapshot"
    assert rollback.rollback_record is None


def test_complete_shadow_session_requires_existing_session(tmp_path: Path) -> None:
    _, orchestrator = build_orchestrator(tmp_path)

    with pytest.raises(ValueError, match="shadow session not found for proposal"):
        orchestrator.complete_shadow_session(
            proposal_id="proposal-missing-shadow",
            comparison_summary="cannot complete without an active session",
            promotion_recommendation=PromotionResult.REJECT,
        )


def test_record_approval_requires_existing_proposal(tmp_path: Path) -> None:
    _, orchestrator = build_orchestrator(tmp_path)

    with pytest.raises(ValueError, match="proposal not found: proposal-missing"):
        orchestrator.record_approval(
            proposal_id="proposal-missing",
            approval_mode=ApprovalMode.MANUAL,
            approval_status=ApprovalStatus.APPROVED,
            approved_by="ops-supervisor",
        )


def test_learning_audit_history_is_queryable_by_proposal_and_time_window(
    tmp_path: Path,
) -> None:
    store, orchestrator = build_orchestrator(tmp_path)
    base_time = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)

    proposal = ChangeProposal(
        proposal_id="proposal-audit-1",
        created_at_utc=base_time,
        source_analysis_id="analysis-audit-1",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="threshold_adjustment",
        changed_parameters=("entry_threshold",),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate ready for audited review",
        evidence_summary="historical replay supports promotion review",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=True,
    )
    pending_approval = ApprovalState(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.SHADOW_THEN_APPROVE,
        approval_status=ApprovalStatus.PENDING,
        updated_at_utc=base_time + timedelta(minutes=5),
        approval_reason="waiting governance review",
    )
    approved_approval = ApprovalState(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.SHADOW_THEN_APPROVE,
        approval_status=ApprovalStatus.APPROVED,
        updated_at_utc=base_time + timedelta(minutes=15),
        approved_by="ops-supervisor",
        approved_at_utc=base_time + timedelta(minutes=15),
        approval_reason="approved after review",
    )
    shadow_session = ShadowEvaluationSession(
        shadow_session_id="shadow-audit-1",
        proposal_id=proposal.proposal_id,
        candidate_version_id="decision-v2",
        baseline_version_id="decision-v1",
        evaluation_scope="shadow-24h",
        started_at_utc=base_time + timedelta(minutes=20),
        ended_at_utc=base_time + timedelta(minutes=80),
        comparison_summary="candidate remained stable across the shadow window",
        promotion_recommendation=PromotionResult.PROMOTE,
    )
    hold_decision = PromotionDecision(
        promotion_id="promotion-audit-1",
        proposal_id=proposal.proposal_id,
        candidate_version_id="decision-v2",
        baseline_version_id="decision-v1",
        evaluated_at_utc=base_time + timedelta(minutes=25),
        promotion_result=PromotionResult.HOLD,
        reason_summary="awaiting full shadow evidence",
    )
    promote_decision = PromotionDecision(
        promotion_id="promotion-audit-2",
        proposal_id=proposal.proposal_id,
        candidate_version_id="decision-v2",
        baseline_version_id="decision-v1",
        evaluated_at_utc=base_time + timedelta(minutes=85),
        promotion_result=PromotionResult.PROMOTE,
        reason_summary="shadow evidence supports promotion",
    )
    rollback_record = RollbackRecord(
        rollback_id="rollback-audit-1",
        triggered_at_utc=base_time + timedelta(minutes=95),
        from_version_id="decision-v2",
        to_snapshot_id="version-snapshot-v1",
        to_version_id="decision-v1",
        rollback_reason="post_activation_guardrail_triggered",
        triggered_by="ops-supervisor",
        rollback_result=RollbackResult.COMPLETED,
    )

    store.write_change_proposal(proposal)
    store.write_approval_state(pending_approval)
    store.write_approval_state(approved_approval)
    store.write_shadow_session(shadow_session)
    store.write_promotion_decision(hold_decision)
    store.write_promotion_decision(promote_decision)
    store.write_rollback_record(rollback_record)

    approvals = orchestrator.list_approval_states(proposal_id=proposal.proposal_id)
    filtered_approvals = orchestrator.list_approval_states(
        proposal_id=proposal.proposal_id,
        start_at_utc=base_time + timedelta(minutes=10),
        end_at_utc=base_time + timedelta(minutes=20),
    )
    proposals = orchestrator.list_change_proposals(
        start_at_utc=base_time - timedelta(minutes=1),
        end_at_utc=base_time + timedelta(minutes=1),
    )
    shadow_sessions = orchestrator.list_shadow_sessions(proposal_id=proposal.proposal_id)
    promotion_decisions = orchestrator.list_promotion_decisions(proposal_id=proposal.proposal_id)
    rollback_records = orchestrator.list_rollback_records(version_id="decision-v2")
    reverse_lookup_rollbacks = orchestrator.list_rollback_records(version_id="decision-v1")

    assert store.read_approval_state(proposal.proposal_id) is not None
    assert [approval.approval_status for approval in approvals] == [
        ApprovalStatus.PENDING,
        ApprovalStatus.APPROVED,
    ]
    assert [approval.approval_status for approval in filtered_approvals] == [
        ApprovalStatus.APPROVED
    ]
    assert [item.proposal_id for item in proposals] == [proposal.proposal_id]
    assert [session.shadow_session_id for session in shadow_sessions] == ["shadow-audit-1"]
    assert [decision.promotion_id for decision in promotion_decisions] == [
        "promotion-audit-1",
        "promotion-audit-2",
    ]
    assert [record.rollback_id for record in rollback_records] == ["rollback-audit-1"]
    assert [record.rollback_id for record in reverse_lookup_rollbacks] == ["rollback-audit-1"]

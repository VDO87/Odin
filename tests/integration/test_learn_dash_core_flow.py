from datetime import timedelta
from pathlib import Path

from core.runtime import CoreRuntimeController
from dash import CoreDashBridge, DashboardControlActionRequest, DashboardPermissionContext
from learn import (
    ApprovalMode,
    ApprovalStatus,
    LearnSnapshotType,
    LearnState,
    LearningOrchestrator,
    PromotionResult,
    RollbackResult,
    VersionActivationRecord,
)
from market import MarketEvaluator, MarketSampleInput
from persistence.sqlite_state_store import SQLiteStateStore
from shared.config import OdinSettings
from shared.enums import GlobalState, OperationalMode
from shared.utils import utc_now


def write_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "odin.local.toml"
    config_path.write_text(
        """
[profile]
name = "full"

[core]
startup_timeout_ms = 15000
event_queue_max_size = 2048
heartbeat_timeout_ms = 500
heartbeat_grace_count = 1
allow_real_mode = false
recovery_required_on_unclean_shutdown = true
persist_on_critical_transition = true

[memory]
enabled = false
provider = "mempalace"
mode = "advisory"
freeze_into_decision_snapshot = true
freeze_into_learn_snapshot = true

[runtime]
state_dir = "__STATE_DIR__"
log_dir = "__LOG_DIR__"
backup_dir = "__BACKUP_DIR__"
memory_dir = "__MEMORY_DIR__"
""".replace("__STATE_DIR__", str(tmp_path / "state"))
        .replace("__LOG_DIR__", str(tmp_path / "logs"))
        .replace("__BACKUP_DIR__", str(tmp_path / "backups"))
        .replace("__MEMORY_DIR__", str(tmp_path / "memory")),
        encoding="utf-8",
    )
    return config_path


def ready_market_event():
    return MarketEvaluator().evaluate(
        MarketSampleInput(
            feed_available=True,
            market_open=True,
            sample_valid=True,
            sample_age_ms=100,
            latency_ms=20,
            spread_bps=1.0,
        )
    ).to_core_event()


def promote_runtime_to_ready(runtime: CoreRuntimeController) -> None:
    runtime.process_event(ready_market_event())
    runtime.process_event(ready_market_event())


def test_dash_projects_pending_learn_proposal_and_approval_state(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    runtime.start()
    promote_runtime_to_ready(runtime)

    orchestrator = LearningOrchestrator(store)
    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-pending-1",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="threshold_adjustment",
        changed_parameters=("entry_threshold",),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate needs approval before activation",
        evidence_summary="candidate has evidence but is still pending review",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=False,
    )
    orchestrator.record_approval(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.MANUAL,
        approval_status=ApprovalStatus.PENDING,
        approval_reason="waiting human review",
    )

    bridge = CoreDashBridge()
    projection = bridge.project_state(
        runtime.get_public_view(),
        DashboardPermissionContext.for_role("sup-1", "supervisor"),
        runtime=runtime,
    )

    assert projection.global_state_model.global_state == GlobalState.READY.value
    assert projection.global_state_model.learn_state == LearnState.WAITING_APPROVAL.value
    assert projection.global_state_model.pending_proposal == proposal.proposal_id
    assert projection.global_state_model.approval_status == ApprovalStatus.PENDING.value
    assert projection.global_state_model.active_version is None
    assert projection.learn_query_results is not None
    assert projection.learn_query_results["LEARN_QUERY_PROPOSAL"]["proposal_id"] == proposal.proposal_id
    assert (
        projection.learn_query_results["LEARN_QUERY_APPROVAL"]["approval_status"]
        == ApprovalStatus.PENDING.value
    )


def test_dash_projects_shadow_pending_without_active_session(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    runtime.start()
    promote_runtime_to_ready(runtime)
    orchestrator = LearningOrchestrator(store)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-shadow-pending-1",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="guard_adjustment",
        changed_parameters=("entry_threshold",),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate still requires shadow start",
        evidence_summary="governance requires a shadow window before activation",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=True,
    )
    orchestrator.record_approval(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.SHADOW_THEN_APPROVE,
        approval_status=ApprovalStatus.APPROVED,
        approved_by="ops-supervisor",
    )

    bridge = CoreDashBridge()
    projection = bridge.project_state(
        runtime.get_public_view(),
        DashboardPermissionContext.for_role("sup-1", "supervisor"),
        runtime=runtime,
    )

    assert projection.global_state_model.learn_state == LearnState.PROPOSAL_GENERATED.value
    assert projection.global_state_model.learn_shadow_audit is not None
    assert projection.global_state_model.learn_shadow_audit["shadow_status"] == "required_pending_start"
    assert projection.learn_query_results is not None
    assert (
        projection.learn_query_results["LEARN_QUERY_SHADOW_AUDIT"]["shadow_status"]
        == "required_pending_start"
    )
    assert "LEARN_ACTION_START_SHADOW" in projection.global_state_model.learn_operational_hints
    assert "LEARN_ACTION_ACTIVATE_PROPOSAL" not in projection.global_state_model.learn_operational_hints
    assert any(alarm.alarm_type == "learn_shadow_pending" for alarm in projection.alarms)


def test_core_and_dash_reflect_learn_activation_and_rollback(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    runtime.start()
    promote_runtime_to_ready(runtime)
    orchestrator = LearningOrchestrator(store)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-activation-1",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="weight_adjustment",
        changed_parameters=("weight_momentum", "weight_volatility"),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate can be activated safely",
        evidence_summary="replay and demo evidence are aligned",
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
    activation = orchestrator.activate_proposal(
        proposal_id=proposal.proposal_id,
        activated_by="ops-supervisor",
        post_activation_monitoring_policy="monitor-4h",
    )
    activated_view = runtime.process_event(activation.to_core_event())

    bridge = CoreDashBridge()
    activated_projection = bridge.project_state(
        activated_view,
        DashboardPermissionContext.for_role("sup-1", "supervisor"),
        runtime=runtime,
    )

    rollback = orchestrator.rollback_active_version(
        rollback_reason="post_activation_degradation_detected",
        triggered_by="ops-supervisor",
    )
    rolled_back_view = runtime.process_event(rollback.to_core_event())
    rolled_back_projection = bridge.project_state(
        rolled_back_view,
        DashboardPermissionContext.for_role("sup-1", "supervisor"),
        runtime=runtime,
    )

    assert activated_view.state_code == GlobalState.READY
    assert activated_projection.global_state_model.learn_state == LearnState.VERSION_ACTIVE_MONITORING.value
    assert activated_projection.global_state_model.active_version == "decision-v2"
    assert activated_projection.global_state_model.rollback_state is None
    assert activated_projection.learn_query_results is not None
    assert activated_projection.learn_query_results["LEARN_QUERY_PROPOSAL"]["proposal_id"] == proposal.proposal_id
    assert activated_projection.learn_query_results["LEARN_QUERY_ACTIVE_VERSION"]["version_id"] == "decision-v2"

    assert rolled_back_view.state_code == GlobalState.READY
    assert rolled_back_projection.global_state_model.learn_state == LearnState.ROLLED_BACK.value
    assert rolled_back_projection.global_state_model.active_version == "decision-v1"
    assert rolled_back_projection.global_state_model.rollback_state == RollbackResult.COMPLETED.value
    assert rolled_back_projection.learn_query_results is not None
    assert (
        rolled_back_projection.learn_query_results["LEARN_QUERY_ROLLBACK_AUDIT"]["rollback_result"]
        == RollbackResult.COMPLETED.value
    )
    assert (
        rolled_back_projection.learn_query_results["LEARN_QUERY_ACTIVE_VERSION"]["version_id"]
        == "decision-v1"
    )
    assert any(alarm.alarm_type == "learn_rollback" for alarm in rolled_back_projection.alarms)


def test_dash_projects_shadow_mode_audit_and_operational_hints(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    runtime.start()
    promote_runtime_to_ready(runtime)
    orchestrator = LearningOrchestrator(store)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-shadow-1",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="risk_guard_adjustment",
        changed_parameters=("stop_loss_multiplier",),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate requires shadow validation first",
        evidence_summary="candidate improved replay but needs governance validation",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=True,
    )
    orchestrator.record_approval(
        proposal_id=proposal.proposal_id,
        approval_mode=ApprovalMode.SHADOW_THEN_APPROVE,
        approval_status=ApprovalStatus.APPROVED,
        approved_by="ops-supervisor",
    )
    running_shadow = orchestrator.start_shadow_session(
        proposal_id=proposal.proposal_id,
        evaluation_scope="shadow-48h",
    )

    bridge = CoreDashBridge()
    running_projection = bridge.project_state(
        runtime.get_public_view(),
        DashboardPermissionContext.for_role("sup-1", "supervisor"),
        runtime=runtime,
    )
    running_shadow_audit = running_projection.global_state_model.learn_shadow_audit

    assert running_projection.global_state_model.learn_state == LearnState.SHADOW_RUNNING.value
    assert running_projection.global_state_model.last_change_summary == proposal.reason_summary
    assert running_shadow_audit is not None
    assert running_shadow_audit["shadow_required"] is True
    assert running_shadow_audit["shadow_status"] == "running"
    assert running_shadow_audit["shadow_session_id"] == running_shadow.shadow_session_id
    assert running_projection.learn_query_results is not None
    assert (
        running_projection.learn_query_results["LEARN_QUERY_SHADOW_AUDIT"]["shadow_session_id"]
        == running_shadow.shadow_session_id
    )
    assert "LEARN_QUERY_SHADOW_AUDIT" in running_projection.global_state_model.learn_operational_hints
    assert "LEARN_ACTION_COMPLETE_SHADOW" in running_projection.global_state_model.learn_operational_hints
    assert any(alarm.alarm_type == "learn_shadow_running" for alarm in running_projection.alarms)

    completed_shadow = orchestrator.complete_shadow_session(
        proposal_id=proposal.proposal_id,
        comparison_summary="candidate underperforms baseline in stress scenario",
        promotion_recommendation=PromotionResult.REJECT,
    )
    completed_projection = bridge.project_state(
        runtime.get_public_view(),
        DashboardPermissionContext.for_role("sup-1", "supervisor"),
        runtime=runtime,
    )
    completed_shadow_audit = completed_projection.global_state_model.learn_shadow_audit

    assert completed_projection.global_state_model.learn_state == LearnState.PROPOSAL_GENERATED.value
    assert completed_shadow_audit is not None
    assert completed_shadow_audit["shadow_status"] == "completed"
    assert completed_shadow_audit["shadow_session_id"] == completed_shadow.shadow_session_id
    assert completed_shadow_audit["promotion_recommendation"] == PromotionResult.REJECT.value
    assert completed_projection.learn_query_results is not None
    assert (
        completed_projection.learn_query_results["LEARN_QUERY_SHADOW_AUDIT"]["comparison_summary"]
        == "candidate underperforms baseline in stress scenario"
    )
    assert (
        completed_projection.learn_query_results["LEARN_QUERY_SHADOW_RECOMMENDATION"][
            "promotion_recommendation"
        ]
        == PromotionResult.REJECT.value
    )
    assert "LEARN_ACTION_ACTIVATE_PROPOSAL" not in completed_projection.global_state_model.learn_operational_hints
    assert "LEARN_QUERY_SHADOW_RECOMMENDATION" in completed_projection.global_state_model.learn_operational_hints
    assert any(alarm.alarm_type == "learn_shadow_recommendation" for alarm in completed_projection.alarms)


def test_dash_projects_shadow_rollback_required_and_blocks_activation(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    runtime.start()
    promote_runtime_to_ready(runtime)
    orchestrator = LearningOrchestrator(store)
    bridge = CoreDashBridge()
    supervisor = DashboardPermissionContext.for_role("sup-1", "supervisor")

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-shadow-rollback-required-1",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="policy_shift",
        changed_parameters=("entry_threshold", "stop_loss_multiplier"),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate finished shadow with rollback-required outcome",
        evidence_summary="shadow comparison found unsafe degradation",
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
        comparison_summary="candidate breached rollback thresholds",
        promotion_recommendation=PromotionResult.ROLLBACK_REQUIRED,
    )

    projection = bridge.project_state(
        runtime.get_public_view(),
        supervisor,
        runtime=runtime,
    )
    activate_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_ACTIVATE_PROPOSAL",
            requested_by="sup-1",
            authorization_context={"proposal_id": proposal.proposal_id},
        ),
        supervisor,
    )

    assert projection.global_state_model.learn_shadow_audit is not None
    assert projection.global_state_model.learn_shadow_audit["promotion_recommendation"] == (
        PromotionResult.ROLLBACK_REQUIRED.value
    )
    assert "LEARN_ACTION_ACTIVATE_PROPOSAL" not in projection.global_state_model.learn_operational_hints
    assert any(alarm.alarm_type == "learn_shadow_recommendation" for alarm in projection.alarms)
    assert activate_result.accepted is False
    assert activate_result.rejection_reason == "action_not_available_for_state"
    assert activate_result.view_payload is not None
    assert (
        activate_result.view_payload["global_state_model"]["learn_shadow_audit"][
            "promotion_recommendation"
        ]
        == PromotionResult.ROLLBACK_REQUIRED.value
    )


def test_learn_audit_history_is_available_for_full_governed_flow(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    runtime.start()
    promote_runtime_to_ready(runtime)
    orchestrator = LearningOrchestrator(store)
    window_start = utc_now() - timedelta(seconds=1)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-audit-2",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="config_bundle",
        changed_parameters=("entry_threshold", "stop_loss_multiplier"),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate enters fully governed audit flow",
        evidence_summary="proposal should leave a queryable governance trail",
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
        approval_status=ApprovalStatus.PENDING,
        approval_reason="awaiting human review",
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
        comparison_summary="candidate remained aligned with baseline",
        promotion_recommendation=PromotionResult.PROMOTE,
    )
    first_decision = orchestrator.evaluate_promotion(proposal_id=proposal.proposal_id)
    activation = orchestrator.activate_proposal(
        proposal_id=proposal.proposal_id,
        activated_by="ops-supervisor",
        post_activation_monitoring_policy="monitor-2h",
    )
    rollback = orchestrator.rollback_active_version(
        rollback_reason="audit rollback drill",
        triggered_by="ops-supervisor",
    )
    runtime.process_event(activation.to_core_event())
    runtime.process_event(rollback.to_core_event())
    window_end = utc_now() + timedelta(seconds=1)

    approvals = orchestrator.list_approval_states(
        proposal_id=proposal.proposal_id,
        start_at_utc=window_start,
        end_at_utc=window_end,
    )
    shadow_sessions = orchestrator.list_shadow_sessions(
        proposal_id=proposal.proposal_id,
        start_at_utc=window_start,
        end_at_utc=window_end,
    )
    promotion_decisions = orchestrator.list_promotion_decisions(
        proposal_id=proposal.proposal_id,
        start_at_utc=window_start,
        end_at_utc=window_end,
    )
    rollback_records = orchestrator.list_rollback_records(
        version_id="decision-v2",
        start_at_utc=window_start,
        end_at_utc=window_end,
    )

    assert first_decision.promotion_result == PromotionResult.PROMOTE
    assert activation.accepted is True
    assert rollback.accepted is True
    assert [approval.approval_status for approval in approvals] == [
        ApprovalStatus.PENDING,
        ApprovalStatus.APPROVED,
    ]
    assert len(shadow_sessions) == 1
    assert shadow_sessions[0].is_completed is True
    assert [decision.promotion_result for decision in promotion_decisions] == [
        PromotionResult.PROMOTE,
        PromotionResult.PROMOTE,
    ]
    assert len(rollback_records) == 1
    assert rollback_records[0].rollback_reason == "audit rollback drill"


def test_dash_projects_learn_history_queries_with_filters(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    runtime.start()
    promote_runtime_to_ready(runtime)
    orchestrator = LearningOrchestrator(store)
    bridge = CoreDashBridge()
    supervisor = DashboardPermissionContext.for_role("sup-1", "supervisor")
    window_start = utc_now() - timedelta(seconds=1)

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-dash-history-1",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="config_bundle",
        changed_parameters=("entry_threshold", "stop_loss_multiplier"),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate for historical query projection",
        evidence_summary="history query should return explicit audit payloads",
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
        approval_status=ApprovalStatus.PENDING,
        approval_reason="awaiting review",
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
        comparison_summary="candidate remained within expected variance",
        promotion_recommendation=PromotionResult.PROMOTE,
    )
    orchestrator.evaluate_promotion(proposal_id=proposal.proposal_id)
    activation = orchestrator.activate_proposal(
        proposal_id=proposal.proposal_id,
        activated_by="ops-supervisor",
        post_activation_monitoring_policy="monitor-2h",
    )
    rollback = orchestrator.rollback_active_version(
        rollback_reason="dash history rollback drill",
        triggered_by="ops-supervisor",
    )
    runtime.process_event(activation.to_core_event())
    runtime.process_event(rollback.to_core_event())
    window_end = utc_now() + timedelta(seconds=1)

    projection = bridge.project_state(
        runtime.get_public_view(),
        supervisor,
        runtime=runtime,
        learn_query_options={
            "proposal_id": proposal.proposal_id,
            "start_at_utc": window_start.isoformat(),
            "end_at_utc": window_end.isoformat(),
        },
    )

    assert projection.learn_query_results is not None
    history = projection.learn_query_results["LEARN_QUERY_HISTORY"]
    assert history["accepted"] is True
    assert history["filters"]["proposal_id"] == proposal.proposal_id
    assert history["counts"]["proposals"] == 1
    assert history["counts"]["approvals"] == 2
    assert history["counts"]["shadow_sessions"] == 1
    assert history["counts"]["promotion_decisions"] == 2
    assert history["counts"]["rollback_records"] == 1
    assert history["proposals"][0]["proposal_id"] == proposal.proposal_id
    assert history["approvals"][0]["approval_status"] == ApprovalStatus.PENDING.value
    assert history["approvals"][1]["approval_status"] == ApprovalStatus.APPROVED.value
    assert history["rollback_records"][0]["rollback_reason"] == "dash history rollback drill"


def test_dash_dispatch_rejects_invalid_learn_actions_with_explicit_reasons(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    runtime.start()
    promote_runtime_to_ready(runtime)
    orchestrator = LearningOrchestrator(store)
    bridge = CoreDashBridge()
    supervisor = DashboardPermissionContext.for_role("sup-1", "supervisor")

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-invalid-actions-1",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="threshold_adjustment",
        changed_parameters=("entry_threshold",),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate exists for invalid action tests",
        evidence_summary="used to verify explicit dispatch rejections",
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
        approval_reason="still pending",
    )
    missing_payload_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_REVIEW_APPROVAL",
            requested_by="sup-1",
            authorization_context={"proposal_id": proposal.proposal_id},
        ),
        supervisor,
    )
    missing_proposal_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_REVIEW_APPROVAL",
            requested_by="sup-1",
            authorization_context={
                "proposal_id": "proposal-missing",
                "approval_mode": ApprovalMode.MANUAL.value,
                "approval_status": ApprovalStatus.APPROVED.value,
            },
        ),
        supervisor,
    )
    missing_shadow_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_COMPLETE_SHADOW",
            requested_by="sup-1",
            authorization_context={
                "proposal_id": proposal.proposal_id,
                "comparison_summary": "cannot complete without a running session",
                "promotion_recommendation": PromotionResult.REJECT.value,
            },
        ),
        supervisor,
    )
    approved_proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-invalid-actions-2",
        base_version_id="decision-v1",
        candidate_version_id="decision-v3",
        change_type="policy_shift",
        changed_parameters=("entry_threshold", "stop_loss_multiplier"),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v3",
        reason_summary="candidate exists for activation blocking tests",
        evidence_summary="used to verify explicit governance blocking in dispatch",
        activation_mode=OperationalMode.DEMO,
        shadow_mode_required=False,
    )
    orchestrator.record_approval(
        proposal_id=approved_proposal.proposal_id,
        approval_mode=ApprovalMode.MANUAL,
        approval_status=ApprovalStatus.APPROVED,
        approved_by="ops-supervisor",
    )
    blocked_activation_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_ACTIVATE_PROPOSAL",
            requested_by="sup-1",
            authorization_context={
                "proposal_id": approved_proposal.proposal_id,
                "activation_allowed": False,
            },
        ),
        supervisor,
    )
    store.write_version_activation(
        VersionActivationRecord(
            version_id="decision-v9",
            previous_version_id="decision-v8",
            activation_mode=ApprovalMode.MANUAL,
            restricted_post_activation=False,
            activated_by="ops-supervisor",
        )
    )
    blocked_rollback_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_TRIGGER_ROLLBACK",
            requested_by="sup-1",
            authorization_context={"rollback_reason": "rollback without active version"},
        ),
        supervisor,
    )

    assert missing_payload_result.accepted is False
    assert missing_payload_result.rejection_reason == "approval_mode_and_status_required"
    assert missing_proposal_result.accepted is False
    assert missing_proposal_result.rejection_reason == "proposal_not_found"
    assert missing_proposal_result.view_payload is not None
    assert (
        missing_proposal_result.view_payload["learn_action_result"]["blocking_reason_code"]
        == "proposal_not_found"
    )
    assert missing_shadow_result.accepted is False
    assert missing_shadow_result.rejection_reason == "action_not_available_for_state"
    assert missing_shadow_result.view_payload is not None
    assert (
        missing_shadow_result.view_payload["global_state_model"]["learn_state"]
        == LearnState.WAITING_APPROVAL.value
    )
    assert blocked_activation_result.accepted is False
    assert blocked_activation_result.rejection_reason == "core_activation_not_allowed"
    assert blocked_activation_result.view_payload is not None
    assert (
        blocked_activation_result.view_payload["learn_action_result"]["blocking_reason_code"]
        == "core_activation_not_allowed"
    )
    assert blocked_rollback_result.accepted is False
    assert blocked_rollback_result.rejection_reason == "missing_recoverable_snapshot"
    assert blocked_rollback_result.view_payload is not None
    assert (
        blocked_rollback_result.view_payload["learn_action_result"]["blocking_reason_code"]
        == "missing_recoverable_snapshot"
    )


def test_dash_dispatch_executes_learn_actions_end_to_end(tmp_path: Path) -> None:
    settings = OdinSettings.load(write_config(tmp_path))
    store = SQLiteStateStore(settings.runtime.state_dir / "core_state.db")
    runtime = CoreRuntimeController(settings, state_store=store)
    runtime.start()
    promote_runtime_to_ready(runtime)
    orchestrator = LearningOrchestrator(store)
    bridge = CoreDashBridge()
    supervisor = DashboardPermissionContext.for_role("sup-1", "supervisor")

    proposal = orchestrator.create_change_proposal(
        source_analysis_id="analysis-dispatch-1",
        base_version_id="decision-v1",
        candidate_version_id="decision-v2",
        change_type="policy_shift",
        changed_parameters=("entry_threshold", "stop_loss_multiplier"),
        old_values_ref="cfg://decision-v1",
        new_values_ref="cfg://decision-v2",
        reason_summary="candidate follows updated policy envelope",
        evidence_summary="stable uplift under replay and constrained demo windows",
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
        approval_status=ApprovalStatus.PENDING,
        approval_reason="waiting governance review",
    )

    review_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_REVIEW_APPROVAL",
            requested_by="sup-1",
            authorization_context={
                "proposal_id": proposal.proposal_id,
                "approval_mode": ApprovalMode.SHADOW_THEN_APPROVE.value,
                "approval_status": ApprovalStatus.APPROVED.value,
                "approval_reason": "approved after review",
            },
        ),
        supervisor,
    )
    start_shadow_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_START_SHADOW",
            requested_by="sup-1",
            authorization_context={
                "proposal_id": proposal.proposal_id,
                "evaluation_scope": "shadow-24h",
            },
        ),
        supervisor,
    )
    complete_shadow_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_COMPLETE_SHADOW",
            requested_by="sup-1",
            authorization_context={
                "proposal_id": proposal.proposal_id,
                "comparison_summary": "candidate tracks baseline with tighter variance",
                "promotion_recommendation": PromotionResult.PROMOTE.value,
            },
        ),
        supervisor,
    )
    evaluate_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_EVALUATE_PROMOTION",
            requested_by="sup-1",
            authorization_context={"proposal_id": proposal.proposal_id},
        ),
        supervisor,
    )
    activate_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_ACTIVATE_PROPOSAL",
            requested_by="sup-1",
            authorization_context={
                "proposal_id": proposal.proposal_id,
                "post_activation_monitoring_policy": "monitor-2h",
            },
        ),
        supervisor,
    )
    rollback_result = bridge.dispatch(
        runtime,
        DashboardControlActionRequest(
            action_type="LEARN_ACTION_TRIGGER_ROLLBACK",
            requested_by="sup-1",
            authorization_context={
                "rollback_reason": "post_activation_drawdown_alert",
            },
        ),
        supervisor,
    )

    assert review_result.accepted is True
    assert review_result.dispatched_event_type == "learn_review_approval"
    assert start_shadow_result.accepted is True
    assert start_shadow_result.view_payload is not None
    assert (
        start_shadow_result.view_payload["global_state_model"]["learn_shadow_audit"]["shadow_status"]
        == "running"
    )
    assert complete_shadow_result.accepted is True
    assert complete_shadow_result.confirmation_required is True
    assert complete_shadow_result.view_payload is not None
    assert (
        complete_shadow_result.view_payload["global_state_model"]["learn_shadow_audit"]["shadow_status"]
        == "completed"
    )
    assert (
        complete_shadow_result.view_payload["learn_query_results"]["LEARN_QUERY_SHADOW_AUDIT"][
            "comparison_summary"
        ]
        == "candidate tracks baseline with tighter variance"
    )
    assert evaluate_result.accepted is True
    assert evaluate_result.view_payload is not None
    assert (
        evaluate_result.view_payload["learn_action_result"]["promotion_decision"]["promotion_result"]
        == PromotionResult.PROMOTE.value
    )
    assert activate_result.accepted is True
    assert activate_result.dispatched_event_type == "EV-LEARN-VERSION-ACTIVATED"
    assert activate_result.view_payload is not None
    assert (
        activate_result.view_payload["global_state_model"]["learn_state"]
        == LearnState.VERSION_ACTIVE_MONITORING.value
    )
    assert rollback_result.accepted is True
    assert rollback_result.dispatched_event_type == "EV-LEARN-ROLLBACK"
    assert rollback_result.view_payload is not None
    assert rollback_result.view_payload["global_state_model"]["learn_state"] == LearnState.ROLLED_BACK.value
    assert (
        rollback_result.view_payload["global_state_model"]["rollback_state"]
        == RollbackResult.COMPLETED.value
    )
    assert (
        rollback_result.view_payload["learn_query_results"]["LEARN_QUERY_ROLLBACK_AUDIT"][
            "rollback_reason"
        ]
        == "post_activation_drawdown_alert"
    )

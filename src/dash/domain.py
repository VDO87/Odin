from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from dash.alarms import AlarmCenter
from dash.availability import ActionAvailabilityResolver
from dash.models import (
    LEARN_ACTIONS,
    LEARN_CONFIRMATION_ACTIONS,
    BlockVectorPanelModel,
    DashboardActionAvailability,
    DashboardControlActionRequest,
    DashboardControlActionResult,
    DashboardGlobalStateModel,
    DashboardPermissionContext,
    DashboardQueryResult,
)
from shared.contracts import (
    CoreEventEnvelope,
    CorePublicStateView,
    ExecutionStateUpdate,
    LearnStateView,
    RecoverySnapshot,
)
from shared.enums import (
    ApprovalMode,
    ApprovalStatus,
    BlockCode,
    DashboardSurface,
    EventType,
    GlobalState,
    LearnState,
    OperationalMode,
    PromotionResult,
    Severity,
)
from shared.utils import ensure_utc, parse_datetime


LEARN_REASON_PROPOSAL_NOT_FOUND = "proposal_not_found"
LEARN_REASON_APPROVAL_NOT_FOUND = "approval_not_found"
LEARN_REASON_SHADOW_SESSION_NOT_FOUND = "shadow_session_not_found"
LEARN_REASON_ACTION_INVALID = "learn_action_invalid"
LEARN_REASON_PROPOSAL_ID_REQUIRED = "proposal_id_required"
LEARN_REASON_APPROVAL_MODE_AND_STATUS_REQUIRED = "approval_mode_and_status_required"
LEARN_REASON_INVALID_APPROVAL_PAYLOAD = "invalid_approval_payload"
LEARN_REASON_EVALUATION_SCOPE_REQUIRED = "evaluation_scope_required"
LEARN_REASON_COMPARISON_AND_RECOMMENDATION_REQUIRED = "comparison_and_recommendation_required"
LEARN_REASON_INVALID_PROMOTION_RECOMMENDATION = "invalid_promotion_recommendation"
LEARN_REASON_ROLLBACK_REASON_REQUIRED = "rollback_reason_required"

DISPATCH_REASON_PERMISSION_DENIED = "permission_denied"
DISPATCH_REASON_ACTION_RESTRICTED = "action_restricted"
DISPATCH_REASON_FEATURE_DISABLED_FOR_PROFILE = "feature_disabled_for_profile"
DISPATCH_REASON_ACTION_NOT_AVAILABLE_FOR_STATE = "action_not_available_for_state"
DISPATCH_REASON_MAINTENANCE_PROFILE_REQUIRED = "maintenance_profile_required"
DISPATCH_REASON_TARGET_MODE_REQUIRED = "target_mode_required"
DISPATCH_REASON_REAL_MODE_REQUIRES_MAINTENANCE_ADMIN = "real_mode_requires_maintenance_admin"


class CoreDashBridge:
    def __init__(self) -> None:
        self._resolver = ActionAvailabilityResolver()
        self._alarm_center = AlarmCenter()

    def _build_learn_shadow_audit(
        self,
        learn_state_view: LearnStateView | None,
    ) -> dict[str, Any] | None:
        if learn_state_view is None:
            return None
        shadow_status = "not_required"
        if learn_state_view.shadow_required and learn_state_view.shadow_session_id is None:
            shadow_status = "required_pending_start"
        elif (
            learn_state_view.shadow_session_id is not None
            and learn_state_view.shadow_ended_at_utc is None
        ):
            shadow_status = "running"
        elif learn_state_view.shadow_session_id is not None:
            shadow_status = "completed"
        return {
            "shadow_required": learn_state_view.shadow_required,
            "shadow_status": shadow_status,
            "shadow_session_id": learn_state_view.shadow_session_id,
            "evaluation_scope": learn_state_view.shadow_scope,
            "started_at_utc": (
                learn_state_view.shadow_started_at_utc.isoformat()
                if learn_state_view.shadow_started_at_utc
                else None
            ),
            "ended_at_utc": (
                learn_state_view.shadow_ended_at_utc.isoformat()
                if learn_state_view.shadow_ended_at_utc
                else None
            ),
            "promotion_recommendation": (
                learn_state_view.shadow_promotion_recommendation.value
                if learn_state_view.shadow_promotion_recommendation
                else None
            ),
        }

    @staticmethod
    def _shadow_required_for_query(
        proposal: Any,
        approval: Any | None,
    ) -> bool:
        return bool(
            proposal.shadow_mode_required
            or (
                approval is not None
                and approval.approval_mode == ApprovalMode.SHADOW_THEN_APPROVE
            )
        )

    def _build_explicit_shadow_audit(
        self,
        proposal: Any,
        approval: Any | None,
        shadow_session: Any | None,
    ) -> dict[str, Any]:
        shadow_required = self._shadow_required_for_query(proposal, approval)
        shadow_status = "not_required"
        if shadow_required and shadow_session is None:
            shadow_status = "required_pending_start"
        elif shadow_session is not None and shadow_session.ended_at_utc is None:
            shadow_status = "running"
        elif shadow_session is not None:
            shadow_status = "completed"
        return {
            "proposal_id": proposal.proposal_id,
            "candidate_version_id": proposal.candidate_version_id,
            "baseline_version_id": proposal.base_version_id,
            "shadow_required": shadow_required,
            "shadow_status": shadow_status,
            "shadow_session_id": (
                shadow_session.shadow_session_id if shadow_session is not None else None
            ),
            "evaluation_scope": (
                shadow_session.evaluation_scope if shadow_session is not None else None
            ),
            "started_at_utc": (
                shadow_session.started_at_utc.isoformat()
                if shadow_session is not None
                else None
            ),
            "ended_at_utc": (
                shadow_session.ended_at_utc.isoformat()
                if shadow_session is not None and shadow_session.ended_at_utc is not None
                else None
            ),
            "comparison_summary": (
                shadow_session.comparison_summary if shadow_session is not None else None
            ),
            "promotion_recommendation": (
                shadow_session.promotion_recommendation.value
                if shadow_session is not None and shadow_session.promotion_recommendation is not None
                else None
            ),
        }

    def _build_learn_query_results(
        self,
        runtime: Any,
        learn_state_view: LearnStateView | None,
        *,
        learn_query_options: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if learn_state_view is None or not self._profile_feature_enabled(runtime, "learn_queries"):
            return None
        learning = self._resolve_learning_orchestrator(runtime)
        latest_proposal = learning.read_latest_change_proposal()
        latest_activation = learning.read_latest_version_activation()
        latest_rollback = learning.read_latest_rollback_record()
        query_results: dict[str, Any] = {}

        if latest_proposal is not None:
            proposal_id = latest_proposal.proposal_id
            approval = learning.read_approval_state(proposal_id=proposal_id)
            shadow_session = learning.read_latest_shadow_session_for_proposal(
                proposal_id=proposal_id
            )

            query_results["LEARN_QUERY_PROPOSAL"] = latest_proposal.to_dict()
            query_results["LEARN_QUERY_APPROVAL"] = (
                approval.to_dict() if approval is not None else None
            )

            if self._shadow_required_for_query(latest_proposal, approval) or shadow_session is not None:
                query_results["LEARN_QUERY_SHADOW_AUDIT"] = self._build_explicit_shadow_audit(
                    latest_proposal,
                    approval,
                    shadow_session,
                )

            if shadow_session is not None and shadow_session.promotion_recommendation is not None:
                query_results["LEARN_QUERY_SHADOW_RECOMMENDATION"] = {
                    "proposal_id": shadow_session.proposal_id,
                    "shadow_session_id": shadow_session.shadow_session_id,
                    "evaluation_scope": shadow_session.evaluation_scope,
                    "comparison_summary": shadow_session.comparison_summary,
                    "promotion_recommendation": shadow_session.promotion_recommendation.value,
                    "started_at_utc": shadow_session.started_at_utc.isoformat(),
                    "ended_at_utc": (
                        shadow_session.ended_at_utc.isoformat()
                        if shadow_session.ended_at_utc is not None
                        else None
                    ),
                }

        if latest_activation is not None:
            query_results["LEARN_QUERY_ACTIVE_VERSION"] = latest_activation.to_dict()
        if latest_rollback is not None:
            query_results["LEARN_QUERY_ROLLBACK_AUDIT"] = latest_rollback.to_dict()

        history_payload = self._build_learn_history_query(
            learning,
            learn_query_options=learn_query_options,
        )
        if history_payload is not None:
            query_results["LEARN_QUERY_HISTORY"] = history_payload

        return query_results or None

    @staticmethod
    def _normalize_learn_query_options(
        learn_query_options: dict[str, Any] | None,
    ) -> tuple[str | None, datetime | None, datetime | None, str | None]:
        if not learn_query_options:
            return None, None, None, None

        proposal_id_raw = learn_query_options.get("proposal_id")
        proposal_id = str(proposal_id_raw).strip() if proposal_id_raw is not None else None
        if proposal_id == "":
            proposal_id = None

        start_raw = learn_query_options.get("start_at_utc")
        end_raw = learn_query_options.get("end_at_utc")

        start_at_utc: datetime | None = None
        if isinstance(start_raw, datetime):
            start_at_utc = ensure_utc(start_raw)
        elif isinstance(start_raw, str) and start_raw.strip():
            normalized = start_raw.strip().replace("Z", "+00:00")
            try:
                start_at_utc = parse_datetime(normalized)
            except ValueError:
                return None, None, None, "invalid_start_at_utc"
            if start_at_utc is None:
                return None, None, None, "invalid_start_at_utc"
        elif start_raw is not None:
            return None, None, None, "invalid_start_at_utc"

        end_at_utc: datetime | None = None
        if isinstance(end_raw, datetime):
            end_at_utc = ensure_utc(end_raw)
        elif isinstance(end_raw, str) and end_raw.strip():
            normalized = end_raw.strip().replace("Z", "+00:00")
            try:
                end_at_utc = parse_datetime(normalized)
            except ValueError:
                return None, None, None, "invalid_end_at_utc"
            if end_at_utc is None:
                return None, None, None, "invalid_end_at_utc"
        elif end_raw is not None:
            return None, None, None, "invalid_end_at_utc"

        if (
            start_at_utc is not None
            and end_at_utc is not None
            and start_at_utc > end_at_utc
        ):
            return None, None, None, "invalid_time_window"
        return proposal_id, start_at_utc, end_at_utc, None

    def _build_learn_history_query(
        self,
        learning: Any,
        *,
        learn_query_options: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not learn_query_options:
            return None

        proposal_id, start_at_utc, end_at_utc, error_code = (
            self._normalize_learn_query_options(learn_query_options)
        )
        if error_code is not None:
            return {
                "accepted": False,
                "error_code": error_code,
            }

        if proposal_id is None and start_at_utc is None and end_at_utc is None:
            return None

        proposals = learning.list_change_proposals(
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )
        if proposal_id is not None:
            proposals = tuple(
                proposal for proposal in proposals if proposal.proposal_id == proposal_id
            )

        approvals = learning.list_approval_states(
            proposal_id=proposal_id,
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )
        shadow_sessions = learning.list_shadow_sessions(
            proposal_id=proposal_id,
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )
        promotion_decisions = learning.list_promotion_decisions(
            proposal_id=proposal_id,
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )

        rollback_records = learning.list_rollback_records(
            version_id=None,
            start_at_utc=start_at_utc,
            end_at_utc=end_at_utc,
        )
        if proposal_id is not None:
            candidate_versions = {
                proposal.candidate_version_id for proposal in proposals
            }
            rollback_records = tuple(
                record
                for record in rollback_records
                if record.from_version_id in candidate_versions
                or record.to_version_id in candidate_versions
            )

        return {
            "accepted": True,
            "filters": {
                "proposal_id": proposal_id,
                "start_at_utc": (
                    start_at_utc.isoformat() if start_at_utc is not None else None
                ),
                "end_at_utc": (
                    end_at_utc.isoformat() if end_at_utc is not None else None
                ),
            },
            "counts": {
                "proposals": len(proposals),
                "approvals": len(approvals),
                "shadow_sessions": len(shadow_sessions),
                "promotion_decisions": len(promotion_decisions),
                "rollback_records": len(rollback_records),
            },
            "proposals": [proposal.to_dict() for proposal in proposals],
            "approvals": [approval.to_dict() for approval in approvals],
            "shadow_sessions": [session.to_dict() for session in shadow_sessions],
            "promotion_decisions": [decision.to_dict() for decision in promotion_decisions],
            "rollback_records": [record.to_dict() for record in rollback_records],
        }

    def _build_learn_operational_hints(
        self,
        learn_state_view: LearnStateView | None,
        *,
        allow_query_hints: bool,
        allow_action_hints: bool,
        learn_query_results: dict[str, Any] | None = None,
    ) -> tuple[str, ...]:
        if learn_state_view is None or (not allow_query_hints and not allow_action_hints):
            return tuple()
        hints: list[str] = []
        shadow_blocks_activation = learn_state_view.shadow_promotion_recommendation in {
            PromotionResult.REJECT,
            PromotionResult.ROLLBACK_REQUIRED,
        }
        if learn_state_view.pending_proposal_id is not None:
            if allow_query_hints:
                hints.extend(["LEARN_QUERY_PROPOSAL", "LEARN_QUERY_APPROVAL"])
            if allow_action_hints:
                hints.append("LEARN_ACTION_EVALUATE_PROMOTION")
        if learn_state_view.shadow_required and learn_state_view.shadow_session_id is None:
            if allow_action_hints:
                hints.append("LEARN_ACTION_START_SHADOW")
        if learn_state_view.shadow_session_id is not None:
            if allow_query_hints:
                hints.append("LEARN_QUERY_SHADOW_AUDIT")
            if allow_action_hints and learn_state_view.shadow_ended_at_utc is None:
                hints.append("LEARN_ACTION_COMPLETE_SHADOW")
        if allow_action_hints and learn_state_view.approval_status == ApprovalStatus.PENDING:
            hints.append("LEARN_ACTION_REVIEW_APPROVAL")
        if (
            allow_action_hints
            and learn_state_view.approval_status == ApprovalStatus.APPROVED
            and (
                not learn_state_view.shadow_required
                or (
                    learn_state_view.shadow_session_id is not None
                    and learn_state_view.shadow_ended_at_utc is not None
                )
            )
            and not shadow_blocks_activation
        ):
            hints.append("LEARN_ACTION_ACTIVATE_PROPOSAL")
        if allow_query_hints and learn_state_view.learn_state in {
            LearnState.VERSION_ACTIVE_MONITORING,
            LearnState.ROLLED_BACK,
        }:
            hints.append("LEARN_QUERY_ACTIVE_VERSION")
        if allow_action_hints and learn_state_view.active_version is not None:
            hints.append("LEARN_ACTION_TRIGGER_ROLLBACK")
        if allow_query_hints and learn_state_view.rollback_state is not None:
            hints.append("LEARN_QUERY_ROLLBACK_AUDIT")
        if allow_query_hints and learn_state_view.shadow_promotion_recommendation in {
            PromotionResult.REJECT,
            PromotionResult.ROLLBACK_REQUIRED,
        }:
            hints.append("LEARN_QUERY_SHADOW_RECOMMENDATION")
        if allow_query_hints and learn_query_results:
            hints.extend(learn_query_results.keys())
        return tuple(dict.fromkeys(hints))

    @staticmethod
    def _parse_bool(value: object, *, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y", "on"}:
                return True
            if normalized in {"0", "false", "no", "n", "off"}:
                return False
        return bool(value)

    @staticmethod
    def _resolve_learning_orchestrator(runtime: Any) -> Any:
        getter = getattr(runtime, "get_learning_orchestrator", None)
        if callable(getter):
            return getter()
        if hasattr(runtime, "_store"):
            from learn import LearningOrchestrator

            return LearningOrchestrator(getattr(runtime, "_store"))
        raise ValueError("runtime does not expose learning orchestrator")

    @staticmethod
    def _resolve_runtime_settings(runtime: Any) -> Any | None:
        getter = getattr(runtime, "get_settings", None)
        if callable(getter):
            return getter()
        return getattr(runtime, "_settings", None)

    @staticmethod
    def _resolve_state_store(runtime: Any) -> Any | None:
        getter = getattr(runtime, "get_state_store", None)
        if callable(getter):
            return getter()
        return getattr(runtime, "_store", None)

    def _dashboard_surface(self, runtime: Any | None) -> DashboardSurface:
        if runtime is None:
            return DashboardSurface.FULL
        settings = self._resolve_runtime_settings(runtime)
        if settings is None:
            return DashboardSurface.FULL
        return getattr(getattr(settings, "dashboard", None), "surface", DashboardSurface.FULL)

    def _profile_feature_enabled(self, runtime: Any | None, feature_name: str) -> bool:
        if runtime is None:
            return True
        checker = getattr(runtime, "is_feature_enabled", None)
        if callable(checker):
            return bool(checker(feature_name))
        settings = self._resolve_runtime_settings(runtime)
        if settings is None:
            return True
        profile = getattr(settings, "profile", None)
        if profile is None:
            return True
        return bool(getattr(profile, f"{feature_name}_enabled", False))

    def _read_latest_execution_ledger(self, runtime: Any | None) -> Any | None:
        if runtime is None:
            return None
        store = self._resolve_state_store(runtime)
        if store is None:
            return None
        reader = getattr(store, "read_latest_execution_ledger_record", None)
        if not callable(reader):
            return None
        return reader()

    def _read_market_runtime_status(self, runtime: Any | None) -> Any | None:
        if runtime is None:
            return None
        reader = getattr(runtime, "get_market_runtime_status", None)
        if not callable(reader):
            return None
        return reader()

    def _build_operation_focus(
        self,
        core_view: CorePublicStateView,
        availability: DashboardActionAvailability,
        *,
        dashboard_surface: DashboardSurface,
        latest_execution_record: Any | None,
        market_runtime_status: Any | None,
    ) -> dict[str, Any]:
        if core_view.kill_active:
            execution_gate = "blocked_kill"
        elif core_view.active_block_vector.active_block_count > 0:
            execution_gate = "blocked"
        elif core_view.state_code in {GlobalState.READY, GlobalState.ACTIVE}:
            execution_gate = "open"
        else:
            execution_gate = "standby"

        payload = {
            "execution_gate": execution_gate,
            "next_actions": list(availability.available_actions),
            "resume_allowed": availability.resume_allowed,
            "active_block_count": core_view.active_block_vector.active_block_count,
            "dominant_block_reason": core_view.dominant_block_reason,
            "kill_active": core_view.kill_active,
            "state_code": core_view.state_code.value,
            "mode_code": core_view.mode_code.value,
            "dashboard_surface": dashboard_surface.value,
        }
        if latest_execution_record is not None:
            payload["last_execution"] = {
                "intent_id": latest_execution_record.intent_id,
                "execution_mode": latest_execution_record.execution_mode.value,
                "exec_state": latest_execution_record.exec_state.value,
                "final_result": (
                    latest_execution_record.final_result.value
                    if latest_execution_record.final_result is not None
                    else None
                ),
                "reason_summary": latest_execution_record.reason_summary,
                "recorded_at_utc": latest_execution_record.recorded_at_utc.isoformat(),
                "audit_ref": latest_execution_record.audit_ref,
                "was_deduplicated": latest_execution_record.was_deduplicated,
            }
        if market_runtime_status is not None:
            serializer = getattr(market_runtime_status, "to_dict", None)
            payload["market_runtime"] = (
                serializer() if callable(serializer) else market_runtime_status
            )
        return payload

    def _build_learn_action_payload(
        self,
        runtime: Any,
        permission_context: DashboardPermissionContext,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        projection = self.project_state(
            runtime.get_public_view(),
            permission_context,
            runtime=runtime,
            recovery_snapshot=recovery_snapshot,
        )
        payload = projection.to_dict()
        if details:
            payload["learn_action_result"] = details
        return payload

    @staticmethod
    def _map_learn_domain_error(error: ValueError) -> tuple[str, str]:
        message = str(error).strip()
        if message.startswith("proposal not found:"):
            return LEARN_REASON_PROPOSAL_NOT_FOUND, message
        if message.startswith("approval not found for proposal:"):
            return LEARN_REASON_APPROVAL_NOT_FOUND, message
        if message == "shadow session not found for proposal":
            return LEARN_REASON_SHADOW_SESSION_NOT_FOUND, message
        return LEARN_REASON_ACTION_INVALID, message or LEARN_REASON_ACTION_INVALID

    def _reject_learn_action(
        self,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
        rejection_reason: str,
        summary: str | None = None,
    ) -> DashboardControlActionResult:
        payload = self._build_learn_action_payload(
            runtime,
            permission_context,
            recovery_snapshot=recovery_snapshot,
            details={
                "accepted": False,
                "blocking_reason_code": rejection_reason,
                "blocking_summary": summary or rejection_reason,
            },
        )
        return DashboardControlActionResult(
            action_id=request.action_id,
            requested_action=request.action_type,
            accepted=False,
            resulting_state=runtime.get_public_view().state_code,
            rejection_reason=rejection_reason,
            view_payload=payload,
        )

    def _handle_learn_review_approval(
        self,
        learning: Any,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        proposal_id: str,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
    ) -> DashboardControlActionResult:
        if not proposal_id:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=LEARN_REASON_PROPOSAL_ID_REQUIRED,
            )
        auth = request.authorization_context
        approval_mode_raw = auth.get("approval_mode")
        approval_status_raw = auth.get("approval_status")
        if approval_mode_raw is None or approval_status_raw is None:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=LEARN_REASON_APPROVAL_MODE_AND_STATUS_REQUIRED,
            )
        try:
            approval_mode = ApprovalMode(str(approval_mode_raw))
            approval_status = ApprovalStatus(str(approval_status_raw))
        except ValueError:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=LEARN_REASON_INVALID_APPROVAL_PAYLOAD,
            )
        approval = learning.record_approval(
            proposal_id=proposal_id,
            approval_mode=approval_mode,
            approval_status=approval_status,
            approval_reason=auth.get("approval_reason"),
            approved_by=auth.get("approved_by", request.requested_by),
        )
        payload = self._build_learn_action_payload(
            runtime,
            permission_context,
            recovery_snapshot=recovery_snapshot,
            details={"approval_state": approval.to_dict()},
        )
        return DashboardControlActionResult(
            action_id=request.action_id,
            requested_action=request.action_type,
            accepted=True,
            resulting_state=runtime.get_public_view().state_code,
            dispatched_event_type="learn_review_approval",
            confirmation_required=True,
            view_payload=payload,
        )

    def _handle_learn_evaluate_promotion(
        self,
        learning: Any,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        proposal_id: str,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
    ) -> DashboardControlActionResult:
        if not proposal_id:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=LEARN_REASON_PROPOSAL_ID_REQUIRED,
            )
        auth = request.authorization_context
        decision = learning.evaluate_promotion(
            proposal_id=proposal_id,
            activation_allowed=self._parse_bool(
                auth.get("activation_allowed"),
                default=True,
            ),
            risk_state_compatible=self._parse_bool(
                auth.get("risk_state_compatible"),
                default=True,
            ),
            requires_restricted_activation=self._parse_bool(
                auth.get("requires_restricted_activation"),
                default=False,
            ),
        )
        payload = self._build_learn_action_payload(
            runtime,
            permission_context,
            recovery_snapshot=recovery_snapshot,
            details={"promotion_decision": decision.to_dict()},
        )
        return DashboardControlActionResult(
            action_id=request.action_id,
            requested_action=request.action_type,
            accepted=True,
            resulting_state=runtime.get_public_view().state_code,
            dispatched_event_type="learn_evaluate_promotion",
            view_payload=payload,
        )

    def _handle_learn_start_shadow(
        self,
        learning: Any,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        proposal_id: str,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
    ) -> DashboardControlActionResult:
        if not proposal_id:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=LEARN_REASON_PROPOSAL_ID_REQUIRED,
            )
        auth = request.authorization_context
        evaluation_scope = str(auth.get("evaluation_scope", "")).strip()
        if not evaluation_scope:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=LEARN_REASON_EVALUATION_SCOPE_REQUIRED,
            )
        session = learning.start_shadow_session(
            proposal_id=proposal_id,
            evaluation_scope=evaluation_scope,
        )
        payload = self._build_learn_action_payload(
            runtime,
            permission_context,
            recovery_snapshot=recovery_snapshot,
            details={"shadow_session": session.to_dict()},
        )
        return DashboardControlActionResult(
            action_id=request.action_id,
            requested_action=request.action_type,
            accepted=True,
            resulting_state=runtime.get_public_view().state_code,
            dispatched_event_type="learn_shadow_started",
            view_payload=payload,
        )

    def _handle_learn_complete_shadow(
        self,
        learning: Any,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        proposal_id: str,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
    ) -> DashboardControlActionResult:
        if not proposal_id:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=LEARN_REASON_PROPOSAL_ID_REQUIRED,
            )
        auth = request.authorization_context
        comparison_summary = str(
            auth.get("comparison_summary") or request.reason_text or ""
        ).strip()
        recommendation_raw = auth.get("promotion_recommendation")
        if not comparison_summary or recommendation_raw is None:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=LEARN_REASON_COMPARISON_AND_RECOMMENDATION_REQUIRED,
            )
        try:
            recommendation = PromotionResult(str(recommendation_raw))
        except ValueError:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=LEARN_REASON_INVALID_PROMOTION_RECOMMENDATION,
            )
        session = learning.complete_shadow_session(
            proposal_id=proposal_id,
            comparison_summary=comparison_summary,
            promotion_recommendation=recommendation,
        )
        payload = self._build_learn_action_payload(
            runtime,
            permission_context,
            recovery_snapshot=recovery_snapshot,
            details={"shadow_session": session.to_dict()},
        )
        return DashboardControlActionResult(
            action_id=request.action_id,
            requested_action=request.action_type,
            accepted=True,
            resulting_state=runtime.get_public_view().state_code,
            dispatched_event_type="learn_shadow_completed",
            confirmation_required=True,
            view_payload=payload,
        )

    def _handle_learn_activate_proposal(
        self,
        learning: Any,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        proposal_id: str,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
    ) -> DashboardControlActionResult:
        if not proposal_id:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=LEARN_REASON_PROPOSAL_ID_REQUIRED,
            )
        auth = request.authorization_context
        activation = learning.activate_proposal(
            proposal_id=proposal_id,
            activated_by=auth.get("activated_by", request.requested_by),
            post_activation_monitoring_policy=auth.get(
                "post_activation_monitoring_policy"
            ),
            activation_allowed=self._parse_bool(
                auth.get("activation_allowed"),
                default=True,
            ),
            risk_state_compatible=self._parse_bool(
                auth.get("risk_state_compatible"),
                default=True,
            ),
            requires_restricted_activation=self._parse_bool(
                auth.get("requires_restricted_activation"),
                default=False,
            ),
        )
        event = activation.to_core_event()
        new_view = runtime.process_event(event)
        payload = self.project_state(
            new_view,
            permission_context,
            runtime=runtime,
            recovery_snapshot=recovery_snapshot,
        ).to_dict()
        payload["learn_action_result"] = {
            "accepted": activation.accepted,
            "promotion_decision": activation.promotion_decision.to_dict(),
            "blocking_reason_code": activation.blocking_reason_code,
            "blocking_summary": activation.blocking_summary,
            "activation_record": (
                activation.activation_record.to_dict()
                if activation.activation_record
                else None
            ),
        }
        return DashboardControlActionResult(
            action_id=request.action_id,
            requested_action=request.action_type,
            accepted=activation.accepted,
            resulting_state=new_view.state_code,
            dispatched_event_type=event.event_type,
            rejection_reason=activation.blocking_reason_code,
            confirmation_required=True,
            view_payload=payload,
        )

    def _handle_learn_trigger_rollback(
        self,
        learning: Any,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        proposal_id: str,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
    ) -> DashboardControlActionResult:
        auth = request.authorization_context
        rollback_reason = str(
            auth.get("rollback_reason") or request.reason_text or ""
        ).strip()
        if not rollback_reason:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=LEARN_REASON_ROLLBACK_REASON_REQUIRED,
            )
        rollback = learning.rollback_active_version(
            rollback_reason=rollback_reason,
            triggered_by=auth.get("triggered_by", request.requested_by),
        )
        event = rollback.to_core_event()
        new_view = runtime.process_event(event)
        payload = self.project_state(
            new_view,
            permission_context,
            runtime=runtime,
            recovery_snapshot=recovery_snapshot,
        ).to_dict()
        payload["learn_action_result"] = {
            "accepted": rollback.accepted,
            "blocking_reason_code": rollback.blocking_reason_code,
            "blocking_summary": rollback.blocking_summary,
            "rollback_record": (
                rollback.rollback_record.to_dict()
                if rollback.rollback_record
                else None
            ),
            "restored_activation": (
                rollback.restored_activation.to_dict()
                if rollback.restored_activation
                else None
            ),
        }
        return DashboardControlActionResult(
            action_id=request.action_id,
            requested_action=request.action_type,
            accepted=rollback.accepted,
            resulting_state=new_view.state_code,
            dispatched_event_type=event.event_type,
            rejection_reason=rollback.blocking_reason_code,
            confirmation_required=True,
            view_payload=payload,
        )

    def _dispatch_learn_action(
        self,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
    ) -> DashboardControlActionResult:
        learning = self._resolve_learning_orchestrator(runtime)
        proposal_id = str(request.authorization_context.get("proposal_id", "")).strip()
        handler_map: dict[str, Callable[..., DashboardControlActionResult]] = {
            "LEARN_ACTION_REVIEW_APPROVAL": self._handle_learn_review_approval,
            "LEARN_ACTION_EVALUATE_PROMOTION": self._handle_learn_evaluate_promotion,
            "LEARN_ACTION_START_SHADOW": self._handle_learn_start_shadow,
            "LEARN_ACTION_COMPLETE_SHADOW": self._handle_learn_complete_shadow,
            "LEARN_ACTION_ACTIVATE_PROPOSAL": self._handle_learn_activate_proposal,
            "LEARN_ACTION_TRIGGER_ROLLBACK": self._handle_learn_trigger_rollback,
        }
        handler = handler_map.get(request.action_type)
        if handler is None:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason="unsupported_learn_action",
            )
        try:
            return handler(
                learning,
                runtime,
                request,
                permission_context,
                proposal_id,
                recovery_snapshot=recovery_snapshot,
            )
        except ValueError as error:
            rejection_reason, summary = self._map_learn_domain_error(error)
            return self._reject_learn_action(
                runtime,
                request,
                permission_context,
                recovery_snapshot=recovery_snapshot,
                rejection_reason=rejection_reason,
                summary=summary,
            )

    def _build_permissioned_availability(
        self,
        *,
        base_availability: DashboardActionAvailability,
        permission_context: DashboardPermissionContext,
        learn_operational_hints: tuple[str, ...],
        learn_actions_enabled: bool,
    ) -> DashboardActionAvailability:
        learn_available_actions = tuple(
            action
            for action in learn_operational_hints
            if action in LEARN_ACTIONS
        )
        expanded_available_actions = tuple(
            dict.fromkeys((*base_availability.available_actions, *learn_available_actions))
        )
        available_actions = tuple(
            action
            for action in expanded_available_actions
            if action in permission_context.granted_actions
            and action not in permission_context.restricted_actions
        )
        all_actions = set(base_availability.forbidden_actions).union(
            set(base_availability.available_actions)
        )
        if learn_actions_enabled:
            all_actions = all_actions.union(set(LEARN_ACTIONS))
        forbidden_actions = tuple(
            action
            for action in sorted(all_actions.difference(available_actions))
        )
        confirmation_required_actions = tuple(
            action
            for action in dict.fromkeys(
                (*base_availability.confirmation_required_actions, *LEARN_CONFIRMATION_ACTIONS)
            )
            if action in available_actions
        )
        return DashboardActionAvailability(
            available_actions=available_actions,
            forbidden_actions=forbidden_actions,
            confirmation_required_actions=confirmation_required_actions,
            maintenance_profile_required=base_availability.maintenance_profile_required,
            resume_allowed="RESUME" in available_actions,
        )

    @staticmethod
    def _build_critical_flags(core_view: CorePublicStateView) -> dict[str, Any]:
        return {
            "kill_active": core_view.kill_active,
            "recovery_required": core_view.state_code == GlobalState.RECOVERY,
            "fault_block_active": core_view.active_block_vector.has_code(BlockCode.FAULT),
            "manual_block_active": core_view.active_block_vector.has_code(BlockCode.MANUAL),
            "risk_block_active": core_view.active_block_vector.has_code(BlockCode.RISK),
        }

    @staticmethod
    def _build_health_summary(core_view: CorePublicStateView) -> dict[str, Any]:
        return {
            "status_summary": core_view.status_summary,
            "readiness_class": core_view.readiness_class.value,
            "integrity_class": core_view.integrity_class.value,
            "active_block_count": core_view.active_block_vector.active_block_count,
            **core_view.health_metrics,
        }

    def _build_global_state_model(
        self,
        *,
        core_view: CorePublicStateView,
        permissioned_availability: DashboardActionAvailability,
        dashboard_surface: DashboardSurface,
        critical_flags: dict[str, Any],
        health_summary: dict[str, Any],
        operation_focus: dict[str, Any],
        learn_state_view: LearnStateView | None,
        learn_shadow_audit: dict[str, Any] | None,
        learn_operational_hints: tuple[str, ...],
    ) -> DashboardGlobalStateModel:
        return DashboardGlobalStateModel(
            global_state=core_view.state_code.value,
            current_mode=core_view.mode_code.value,
            dashboard_profile=dashboard_surface.value,
            state_updated_at_utc=core_view.last_transition["at_utc"],
            dominant_block_reason=core_view.dominant_block_reason,
            active_block_vector=core_view.active_block_vector.to_dict(),
            available_actions=permissioned_availability.available_actions,
            critical_flags=critical_flags,
            heartbeat_health_summary=core_view.critical_module_liveness,
            health_summary=health_summary,
            operation_focus=operation_focus,
            learn_state=learn_state_view.learn_state.value if learn_state_view else None,
            active_version=learn_state_view.active_version if learn_state_view else None,
            pending_proposal=learn_state_view.pending_proposal_id if learn_state_view else None,
            approval_status=(
                learn_state_view.approval_status.value
                if learn_state_view and learn_state_view.approval_status
                else None
            ),
            rollback_state=(
                learn_state_view.rollback_state.value
                if learn_state_view and learn_state_view.rollback_state
                else None
            ),
            last_change_summary=learn_state_view.last_change_summary if learn_state_view else None,
            learn_shadow_audit=learn_shadow_audit,
            learn_operational_hints=learn_operational_hints,
        )

    @staticmethod
    def _build_block_panel(core_view: CorePublicStateView) -> BlockVectorPanelModel:
        return BlockVectorPanelModel(
            dominant_block_reason=core_view.dominant_block_reason,
            active_block_vector=core_view.active_block_vector.to_dict(),
            block_count=core_view.active_block_vector.active_block_count,
            has_manual_block=core_view.active_block_vector.has_code(BlockCode.MANUAL),
            has_kill_block=core_view.active_block_vector.has_code(BlockCode.KILL),
            has_fault_block=core_view.active_block_vector.has_code(BlockCode.FAULT),
        )

    @staticmethod
    def _build_recovery_panel(
        recovery_snapshot: RecoverySnapshot | None,
    ) -> dict[str, Any] | None:
        if recovery_snapshot is None:
            return None
        return {
            "recovery_state": recovery_snapshot.result.recovery_state.value
            if recovery_snapshot.result.recovery_state
            else None,
            "incident_type": recovery_snapshot.result.incident_type.value
            if recovery_snapshot.result.incident_type
            else None,
            "recovery_result": recovery_snapshot.result.result_code.value,
            "manual_intervention_required": recovery_snapshot.result.manual_intervention_required,
            "reconciliation_confidence": recovery_snapshot.result.reconciliation_confidence,
        }

    def project_state(
        self,
        core_view: CorePublicStateView,
        permission_context: DashboardPermissionContext,
        *,
        runtime: Any | None = None,
        recovery_snapshot: RecoverySnapshot | None = None,
        latest_exec_update: ExecutionStateUpdate | None = None,
        learn_query_options: dict[str, Any] | None = None,
    ) -> DashboardQueryResult:
        base_availability = self._resolver.resolve(core_view, recovery_snapshot=recovery_snapshot)
        dashboard_surface = self._dashboard_surface(runtime)
        learn_queries_enabled = self._profile_feature_enabled(runtime, "learn_queries")
        learn_actions_enabled = self._profile_feature_enabled(runtime, "learn_actions")
        learn_state_view = core_view.learn_state_view
        learn_shadow_audit = (
            self._build_learn_shadow_audit(learn_state_view) if learn_queries_enabled else None
        )
        learn_query_results = (
            self._build_learn_query_results(
                runtime,
                learn_state_view,
                learn_query_options=learn_query_options,
            )
            if runtime is not None
            else None
        )
        learn_operational_hints = self._build_learn_operational_hints(
            learn_state_view,
            allow_query_hints=learn_queries_enabled,
            allow_action_hints=learn_actions_enabled,
            learn_query_results=learn_query_results,
        )
        permissioned_availability = self._build_permissioned_availability(
            base_availability=base_availability,
            permission_context=permission_context,
            learn_operational_hints=learn_operational_hints,
            learn_actions_enabled=learn_actions_enabled,
        )
        critical_flags = self._build_critical_flags(core_view)
        health_summary = self._build_health_summary(core_view)
        latest_execution_record = self._read_latest_execution_ledger(runtime)
        market_runtime_status = self._read_market_runtime_status(runtime)
        operation_focus = self._build_operation_focus(
            core_view,
            permissioned_availability,
            dashboard_surface=dashboard_surface,
            latest_execution_record=latest_execution_record,
            market_runtime_status=market_runtime_status,
        )
        global_state_model = self._build_global_state_model(
            core_view=core_view,
            permissioned_availability=permissioned_availability,
            dashboard_surface=dashboard_surface,
            critical_flags=critical_flags,
            health_summary=health_summary,
            operation_focus=operation_focus,
            learn_state_view=learn_state_view,
            learn_shadow_audit=learn_shadow_audit,
            learn_operational_hints=learn_operational_hints,
        )
        block_panel = self._build_block_panel(core_view)
        recovery_panel = self._build_recovery_panel(recovery_snapshot)
        return DashboardQueryResult(
            global_state_model=global_state_model,
            block_vector_panel=block_panel,
            alarms=self._alarm_center.build(
                core_view,
                recovery_snapshot=recovery_snapshot,
                latest_exec_update=latest_exec_update,
            ),
            action_availability=permissioned_availability,
            learn_query_results=learn_query_results,
            recovery_panel=recovery_panel,
        )

    def dispatch(
        self,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
    ) -> DashboardControlActionResult:
        core_view = runtime.get_public_view()
        projection = self.project_state(
            core_view,
            permission_context,
            runtime=runtime,
            recovery_snapshot=recovery_snapshot,
        )
        precheck = self._validate_dispatch_preconditions(
            runtime,
            request,
            permission_context,
            projection,
            core_view,
        )
        if precheck is not None:
            return precheck

        if request.action_type in LEARN_ACTIONS:
            return self._dispatch_learn_action(
                runtime,
                request,
                permission_context,
                recovery_snapshot=recovery_snapshot,
            )

        if request.action_type == "START" and core_view.state_code == GlobalState.OFFLINE:
            return self._handle_start_dispatch_action(runtime, request, permission_context)
        if request.action_type == "EXPORT_LOGS":
            return self._handle_export_logs_dispatch_action(core_view, projection, request)

        return self._handle_event_dispatch_action(
            runtime,
            request,
            permission_context,
            projection,
            recovery_snapshot=recovery_snapshot,
        )

    def _validate_dispatch_preconditions(
        self,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        projection: DashboardQueryResult,
        core_view: CorePublicStateView,
    ) -> DashboardControlActionResult | None:
        if request.action_type not in permission_context.granted_actions:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=DISPATCH_REASON_PERMISSION_DENIED,
            )
        if request.action_type in permission_context.restricted_actions:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=DISPATCH_REASON_ACTION_RESTRICTED,
            )
        if request.action_type in LEARN_ACTIONS and not self._profile_feature_enabled(
            runtime, "learn_actions"
        ):
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=DISPATCH_REASON_FEATURE_DISABLED_FOR_PROFILE,
                view_payload=projection.to_dict(),
            )
        if request.action_type not in projection.action_availability.available_actions:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=DISPATCH_REASON_ACTION_NOT_AVAILABLE_FOR_STATE,
                view_payload=projection.to_dict(),
            )
        if request.action_type == "MAINTENANCE_ENTER" and not request.maintenance_profile:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=DISPATCH_REASON_MAINTENANCE_PROFILE_REQUIRED,
                confirmation_required=True,
            )
        if request.action_type == "MODE_CHANGE" and request.target_mode is None:
            return DashboardControlActionResult(
                action_id=request.action_id,
                requested_action=request.action_type,
                accepted=False,
                rejection_reason=DISPATCH_REASON_TARGET_MODE_REQUIRED,
                confirmation_required=True,
            )
        return self._validate_mode_change_preconditions(
            runtime,
            request,
            permission_context,
            projection,
            core_view,
        )

    def _validate_mode_change_preconditions(
        self,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        projection: DashboardQueryResult,
        core_view: CorePublicStateView,
    ) -> DashboardControlActionResult | None:
        if request.action_type == "MODE_CHANGE" and request.target_mode == OperationalMode.REAL:
            if permission_context.role != "maintenance_admin":
                return DashboardControlActionResult(
                    action_id=request.action_id,
                    requested_action=request.action_type,
                    accepted=False,
                    rejection_reason=DISPATCH_REASON_REAL_MODE_REQUIRES_MAINTENANCE_ADMIN,
                    confirmation_required=True,
                )
            allowed, rejection_reason = runtime.validate_mode_change_request(
                request.target_mode,
                authorization_context=request.authorization_context,
                reason_text=request.reason_text,
            )
            if not allowed:
                return DashboardControlActionResult(
                    action_id=request.action_id,
                    requested_action=request.action_type,
                    accepted=False,
                    rejection_reason=rejection_reason,
                    confirmation_required=True,
                    view_payload=projection.to_dict(),
                )
        if (
            request.action_type == "MODE_CHANGE"
            and core_view.mode_code == OperationalMode.REAL
            and request.target_mode != OperationalMode.REAL
        ):
            allowed, rejection_reason = runtime.validate_mode_change_request(
                request.target_mode,
                authorization_context=request.authorization_context,
                reason_text=request.reason_text,
            )
            if not allowed:
                return DashboardControlActionResult(
                    action_id=request.action_id,
                    requested_action=request.action_type,
                    accepted=False,
                    rejection_reason=rejection_reason,
                    confirmation_required=True,
                    view_payload=projection.to_dict(),
                )
        return None

    def _handle_start_dispatch_action(
        self,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
    ) -> DashboardControlActionResult:
        new_view = runtime.start()
        return DashboardControlActionResult(
            action_id=request.action_id,
            requested_action=request.action_type,
            accepted=True,
            resulting_state=new_view.state_code,
            dispatched_event_type=EventType.START.value,
            view_payload=self.project_state(
                new_view,
                permission_context,
                runtime=runtime,
            ).to_dict(),
        )

    def _handle_export_logs_dispatch_action(
        self,
        core_view: CorePublicStateView,
        projection: DashboardQueryResult,
        request: DashboardControlActionRequest,
    ) -> DashboardControlActionResult:
        export_path = Path(
            str(
                request.authorization_context.get(
                    "export_path", f"dashboard-export-{request.action_id}.json"
                )
            )
        )
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(
            json.dumps(projection.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        payload = projection.to_dict()
        payload["export_path"] = str(export_path)
        return DashboardControlActionResult(
            action_id=request.action_id,
            requested_action=request.action_type,
            accepted=True,
            resulting_state=core_view.state_code,
            dispatched_event_type="dash_export_logs",
            view_payload=payload,
        )

    def _handle_event_dispatch_action(
        self,
        runtime: Any,
        request: DashboardControlActionRequest,
        permission_context: DashboardPermissionContext,
        projection: DashboardQueryResult,
        *,
        recovery_snapshot: RecoverySnapshot | None = None,
    ) -> DashboardControlActionResult:
        event = self._map_request_to_event(request)
        new_view = runtime.process_event(event)
        return DashboardControlActionResult(
            action_id=request.action_id,
            requested_action=request.action_type,
            accepted=True,
            resulting_state=new_view.state_code,
            dispatched_event_type=event.event_type,
            confirmation_required=(
                request.action_type
                in projection.action_availability.confirmation_required_actions
            ),
            view_payload=self.project_state(
                new_view,
                permission_context,
                runtime=runtime,
                recovery_snapshot=recovery_snapshot,
            ).to_dict(),
        )

    def _map_request_to_event(self, request: DashboardControlActionRequest) -> CoreEventEnvelope:
        event_map = {
            "STOP": EventType.STOP.value,
            "PAUSE": EventType.PAUSE.value,
            "RESUME": EventType.RESUME.value,
            "MANUAL_BLOCK": EventType.MANUAL_BLOCK.value,
            "MANUAL_CLEAR": EventType.MANUAL_CLEAR.value,
            "MODE_CHANGE": EventType.MODE_CHANGE.value,
            "MAINTENANCE_ENTER": EventType.MAINTENANCE_ENTER.value,
            "MAINTENANCE_EXIT": EventType.MAINTENANCE_EXIT.value,
            "REQUEST_RECOVERY_VALIDATION": EventType.RECOVERY_START.value,
        }
        event_type = event_map.get(request.action_type)
        if event_type is None:
            raise ValueError(f"unsupported dashboard action: {request.action_type}")

        payload = {
            "requested_action": request.action_type,
            "operator_id": request.requested_by,
            "authorization_context": request.authorization_context,
            "reason_code": request.authorization_context.get("reason_code", request.action_type.lower()),
        }
        if request.reason_text:
            payload["reason_text"] = request.reason_text
        if request.maintenance_profile:
            payload["maintenance_profile"] = request.maintenance_profile
        if request.target_mode is not None:
            payload["mode_code"] = request.target_mode.value
            if request.target_mode == OperationalMode.REAL:
                payload["real_mode_confirmation"] = request.authorization_context.get(
                    "real_mode_confirmation"
                )
                payload["change_ticket"] = request.authorization_context.get("change_ticket")
                payload["approval_ref"] = request.authorization_context.get("approval_ref")
                payload["approved_by"] = request.authorization_context.get("approved_by")
            if request.target_mode != OperationalMode.REAL:
                payload["rollback_reason"] = request.authorization_context.get("rollback_reason")

        return CoreEventEnvelope(
            event_type=event_type,
            source_module="DASH",
            severity=Severity.INFO,
            payload=payload,
        )

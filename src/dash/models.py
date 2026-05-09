from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from shared.enums import GlobalState, OperationalMode
from shared.utils import ensure_utc, make_id, utc_now


LEARN_ACTIONS: tuple[str, ...] = (
    "LEARN_ACTION_REVIEW_APPROVAL",
    "LEARN_ACTION_EVALUATE_PROMOTION",
    "LEARN_ACTION_START_SHADOW",
    "LEARN_ACTION_COMPLETE_SHADOW",
    "LEARN_ACTION_ACTIVATE_PROPOSAL",
    "LEARN_ACTION_TRIGGER_ROLLBACK",
)

LEARN_CONFIRMATION_ACTIONS: tuple[str, ...] = (
    "LEARN_ACTION_REVIEW_APPROVAL",
    "LEARN_ACTION_COMPLETE_SHADOW",
    "LEARN_ACTION_ACTIVATE_PROPOSAL",
    "LEARN_ACTION_TRIGGER_ROLLBACK",
)


ROLE_ACTIONS: dict[str, tuple[str, ...]] = {
    "viewer": tuple(),
    "operator": ("START", "STOP", "PAUSE", "RESUME", "EXPORT_LOGS"),
    "supervisor": (
        "START",
        "STOP",
        "PAUSE",
        "RESUME",
        "MANUAL_BLOCK",
        "MANUAL_CLEAR",
        "MODE_CHANGE",
        "REQUEST_RECOVERY_VALIDATION",
        "EXPORT_LOGS",
        *LEARN_ACTIONS,
    ),
    "maintenance_admin": (
        "START",
        "STOP",
        "PAUSE",
        "RESUME",
        "MANUAL_BLOCK",
        "MANUAL_CLEAR",
        "MODE_CHANGE",
        "MAINTENANCE_ENTER",
        "MAINTENANCE_EXIT",
        "REQUEST_RECOVERY_VALIDATION",
        "EXPORT_LOGS",
        *LEARN_ACTIONS,
    ),
}


@dataclass(frozen=True, slots=True)
class DashboardPermissionContext:
    principal_id: str
    role: str
    granted_actions: tuple[str, ...]
    restricted_actions: tuple[str, ...] = tuple()
    session_started_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "session_started_at_utc", ensure_utc(self.session_started_at_utc))
        if not self.principal_id:
            raise ValueError("principal_id is required")
        if not self.role:
            raise ValueError("role is required")

    @classmethod
    def for_role(cls, principal_id: str, role: str) -> "DashboardPermissionContext":
        if role not in ROLE_ACTIONS:
            raise ValueError(f"unsupported role: {role}")
        return cls(principal_id=principal_id, role=role, granted_actions=ROLE_ACTIONS[role])


@dataclass(frozen=True, slots=True)
class DashboardControlActionRequest:
    action_type: str
    requested_by: str
    authorization_context: dict[str, Any]
    action_id: str = field(default_factory=lambda: make_id("dash-action"))
    requested_at_utc: datetime = field(default_factory=utc_now)
    reason_text: str | None = None
    maintenance_profile: str | None = None
    target_mode: OperationalMode | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested_at_utc", ensure_utc(self.requested_at_utc))
        if not self.action_type:
            raise ValueError("action_type is required")
        if not self.requested_by:
            raise ValueError("requested_by is required")


@dataclass(frozen=True, slots=True)
class DashboardControlActionResult:
    action_id: str
    requested_action: str
    accepted: bool
    resulting_state: GlobalState | None = None
    dispatched_event_type: str | None = None
    rejection_reason: str | None = None
    confirmation_required: bool = False
    view_payload: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class DashboardActionAvailability:
    available_actions: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    confirmation_required_actions: tuple[str, ...]
    maintenance_profile_required: bool
    resume_allowed: bool


@dataclass(frozen=True, slots=True)
class DashboardAlarmItem:
    severity: str
    alarm_type: str
    source_module: str
    title: str
    summary: str
    is_active: bool = True
    linked_state_ref: str | None = None
    alarm_id: str = field(default_factory=lambda: make_id("alarm"))
    created_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "alarm_id": self.alarm_id,
            "severity": self.severity,
            "alarm_type": self.alarm_type,
            "source_module": self.source_module,
            "created_at_utc": self.created_at_utc.isoformat(),
            "is_active": self.is_active,
            "title": self.title,
            "summary": self.summary,
            "linked_state_ref": self.linked_state_ref,
        }


@dataclass(frozen=True, slots=True)
class BlockVectorPanelModel:
    dominant_block_reason: str | None
    active_block_vector: dict[str, Any]
    block_count: int
    has_manual_block: bool
    has_kill_block: bool
    has_fault_block: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "dominant_block_reason": self.dominant_block_reason,
            "active_block_vector": self.active_block_vector,
            "block_count": self.block_count,
            "has_manual_block": self.has_manual_block,
            "has_kill_block": self.has_kill_block,
            "has_fault_block": self.has_fault_block,
        }


@dataclass(frozen=True, slots=True)
class DashboardGlobalStateModel:
    global_state: str
    current_mode: str
    dashboard_profile: str
    state_updated_at_utc: str
    available_actions: tuple[str, ...]
    critical_flags: dict[str, Any]
    heartbeat_health_summary: dict[str, str]
    dominant_block_reason: str | None = None
    active_block_vector: dict[str, Any] | None = None
    health_summary: dict[str, Any] | None = None
    operation_focus: dict[str, Any] | None = None
    learn_state: str | None = None
    active_version: str | None = None
    pending_proposal: str | None = None
    approval_status: str | None = None
    rollback_state: str | None = None
    last_change_summary: str | None = None
    learn_shadow_audit: dict[str, Any] | None = None
    learn_operational_hints: tuple[str, ...] = tuple()

    def to_dict(self) -> dict[str, Any]:
        return {
            "global_state": self.global_state,
            "current_mode": self.current_mode,
            "dashboard_profile": self.dashboard_profile,
            "state_updated_at_utc": self.state_updated_at_utc,
            "dominant_block_reason": self.dominant_block_reason,
            "active_block_vector": self.active_block_vector,
            "available_actions": list(self.available_actions),
            "critical_flags": self.critical_flags,
            "heartbeat_health_summary": self.heartbeat_health_summary,
            "health_summary": self.health_summary,
            "operation_focus": self.operation_focus,
            "learn_state": self.learn_state,
            "active_version": self.active_version,
            "pending_proposal": self.pending_proposal,
            "approval_status": self.approval_status,
            "rollback_state": self.rollback_state,
            "last_change_summary": self.last_change_summary,
            "learn_shadow_audit": self.learn_shadow_audit,
            "learn_operational_hints": list(self.learn_operational_hints),
        }


@dataclass(frozen=True, slots=True)
class DashboardQueryResult:
    global_state_model: DashboardGlobalStateModel
    block_vector_panel: BlockVectorPanelModel
    alarms: tuple[DashboardAlarmItem, ...]
    action_availability: DashboardActionAvailability
    learn_query_results: dict[str, Any] | None = None
    recovery_panel: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "global_state_model": self.global_state_model.to_dict(),
            "block_vector_panel": self.block_vector_panel.to_dict(),
            "alarms": [alarm.to_dict() for alarm in self.alarms],
            "action_availability": {
                "available_actions": list(self.action_availability.available_actions),
                "forbidden_actions": list(self.action_availability.forbidden_actions),
                "confirmation_required_actions": list(
                    self.action_availability.confirmation_required_actions
                ),
                "maintenance_profile_required": self.action_availability.maintenance_profile_required,
                "resume_allowed": self.action_availability.resume_allowed,
            },
            "learn_query_results": self.learn_query_results,
            "recovery_panel": self.recovery_panel,
        }

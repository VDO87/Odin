from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from shared.enums import (
    BlockCode,
    GlobalState,
    HeartbeatStatus,
    IntegrityClass,
    OperationalMode,
    ReadinessClass,
    Severity,
)
from shared.utils import ensure_utc, isoformat_utc, make_id, parse_datetime, utc_now

if TYPE_CHECKING:
    from shared.contracts_parts.learn import LearnStateView


@dataclass(frozen=True, slots=True)
class CoreEventEnvelope:
    event_type: str
    source_module: str
    severity: Severity
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: make_id("event"))
    timestamp_utc: datetime = field(default_factory=utc_now)
    correlation_id: str | None = None
    payload_schema_version: str = "1.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp_utc", ensure_utc(self.timestamp_utc))
        if not self.event_type:
            raise ValueError("event_type is required")
        if not self.source_module:
            raise ValueError("source_module is required")
        if not self.payload_schema_version:
            raise ValueError("payload_schema_version is required")


@dataclass(frozen=True, slots=True)
class BlockEntry:
    block_code: BlockCode
    source_module: str
    severity: Severity
    reason_code: str
    manual_clear_required: bool
    clearable_by_recovery: bool
    reason_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    block_id: str = field(default_factory=lambda: make_id("block"))
    created_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "block_code": self.block_code.value,
            "source_module": self.source_module,
            "created_at_utc": isoformat_utc(self.created_at_utc),
            "severity": self.severity.value,
            "reason_code": self.reason_code,
            "reason_text": self.reason_text,
            "manual_clear_required": self.manual_clear_required,
            "clearable_by_recovery": self.clearable_by_recovery,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BlockEntry":
        return cls(
            block_id=data["block_id"],
            block_code=BlockCode(data["block_code"]),
            source_module=data["source_module"],
            created_at_utc=parse_datetime(data["created_at_utc"]) or utc_now(),
            severity=Severity(data["severity"]),
            reason_code=data["reason_code"],
            reason_text=data.get("reason_text"),
            manual_clear_required=bool(data["manual_clear_required"]),
            clearable_by_recovery=bool(data["clearable_by_recovery"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ActiveBlockVector:
    blocks: tuple[BlockEntry, ...]
    dominant_block_reason: str | None
    dominant_block_priority: int
    manual_clear_required: bool
    vector_id: str = field(default_factory=lambda: make_id("vector"))
    updated_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "updated_at_utc", ensure_utc(self.updated_at_utc))

    @property
    def active_block_count(self) -> int:
        return len(self.blocks)

    @classmethod
    def empty(cls) -> "ActiveBlockVector":
        return cls(
            blocks=tuple(),
            dominant_block_reason=None,
            dominant_block_priority=0,
            manual_clear_required=False,
        )

    def has_code(self, code: BlockCode) -> bool:
        return any(block.block_code == code for block in self.blocks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vector_id": self.vector_id,
            "updated_at_utc": isoformat_utc(self.updated_at_utc),
            "dominant_block_reason": self.dominant_block_reason,
            "dominant_block_priority": self.dominant_block_priority,
            "manual_clear_required": self.manual_clear_required,
            "blocks": [block.to_dict() for block in self.blocks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActiveBlockVector":
        return cls(
            vector_id=data["vector_id"],
            updated_at_utc=parse_datetime(data["updated_at_utc"]) or utc_now(),
            dominant_block_reason=data.get("dominant_block_reason"),
            dominant_block_priority=int(data.get("dominant_block_priority", 0)),
            manual_clear_required=bool(data.get("manual_clear_required", False)),
            blocks=tuple(BlockEntry.from_dict(item) for item in data.get("blocks", [])),
        )


@dataclass(frozen=True, slots=True)
class ModuleHeartbeat:
    module_name: str
    emitted_at_utc: datetime
    observed_at_utc: datetime
    status_code: HeartbeatStatus
    consecutive_failures: int
    timeout_threshold_ms: int
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "emitted_at_utc", ensure_utc(self.emitted_at_utc))
        object.__setattr__(self, "observed_at_utc", ensure_utc(self.observed_at_utc))


@dataclass(frozen=True, slots=True)
class PersistentKillState:
    is_active: bool
    source_module: str
    reason_code: str
    activated_at_utc: datetime = field(default_factory=utc_now)
    manual_clear_required: bool = True
    reason_text: str | None = None
    activated_by: str | None = None
    cleared_at_utc: datetime | None = None
    cleared_by: str | None = None
    clear_audit_ref: str | None = None
    kill_id: str = field(default_factory=lambda: make_id("kill"))

    def __post_init__(self) -> None:
        object.__setattr__(self, "activated_at_utc", ensure_utc(self.activated_at_utc))
        if self.cleared_at_utc is not None:
            object.__setattr__(self, "cleared_at_utc", ensure_utc(self.cleared_at_utc))

    @classmethod
    def inactive(cls) -> "PersistentKillState":
        return cls(is_active=False, source_module="system", reason_code="inactive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kill_id": self.kill_id,
            "is_active": self.is_active,
            "activated_at_utc": isoformat_utc(self.activated_at_utc),
            "activated_by": self.activated_by,
            "source_module": self.source_module,
            "reason_code": self.reason_code,
            "reason_text": self.reason_text,
            "manual_clear_required": self.manual_clear_required,
            "cleared_at_utc": isoformat_utc(self.cleared_at_utc)
            if self.cleared_at_utc
            else None,
            "cleared_by": self.cleared_by,
            "clear_audit_ref": self.clear_audit_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersistentKillState":
        return cls(
            kill_id=data["kill_id"],
            is_active=bool(data["is_active"]),
            activated_at_utc=parse_datetime(data["activated_at_utc"]) or utc_now(),
            activated_by=data.get("activated_by"),
            source_module=data["source_module"],
            reason_code=data["reason_code"],
            reason_text=data.get("reason_text"),
            manual_clear_required=bool(data.get("manual_clear_required", True)),
            cleared_at_utc=parse_datetime(data.get("cleared_at_utc")),
            cleared_by=data.get("cleared_by"),
            clear_audit_ref=data.get("clear_audit_ref"),
        )


@dataclass(frozen=True, slots=True)
class ShutdownMarker:
    clean_shutdown: bool
    startup_in_progress: bool
    happened_at_utc: datetime
    marker_id: str = field(default_factory=lambda: make_id("marker"))

    def __post_init__(self) -> None:
        object.__setattr__(self, "happened_at_utc", ensure_utc(self.happened_at_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker_id": self.marker_id,
            "clean_shutdown": self.clean_shutdown,
            "startup_in_progress": self.startup_in_progress,
            "happened_at_utc": isoformat_utc(self.happened_at_utc),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShutdownMarker":
        return cls(
            marker_id=data["marker_id"],
            clean_shutdown=bool(data["clean_shutdown"]),
            startup_in_progress=bool(data["startup_in_progress"]),
            happened_at_utc=parse_datetime(data["happened_at_utc"]) or utc_now(),
        )


@dataclass(frozen=True, slots=True)
class StartupValidationResult:
    configuration_ok: bool
    persistence_ok: bool
    required_modules_ok: bool
    kill_active: bool
    block_vector_loaded: bool
    recommended_entry_state: GlobalState
    operator_action_required: bool
    validation_notes: tuple[str, ...] = tuple()
    startup_id: str = field(default_factory=lambda: make_id("startup"))


@dataclass(frozen=True, slots=True)
class TransitionGuardResult:
    event_id: str
    from_state: GlobalState
    requested_to_state: GlobalState
    allowed: bool
    evaluated_at_utc: datetime = field(default_factory=utc_now)
    blocking_reason_code: str | None = None
    required_operator_action: str | None = None
    guard_result_id: str = field(default_factory=lambda: make_id("guard"))

    def __post_init__(self) -> None:
        object.__setattr__(self, "evaluated_at_utc", ensure_utc(self.evaluated_at_utc))


@dataclass(frozen=True, slots=True)
class GlobalStateSnapshot:
    state_code: GlobalState
    mode_code: OperationalMode
    last_transition_event: str
    last_transition_at_utc: datetime
    readiness_class: ReadinessClass
    integrity_class: IntegrityClass
    kill_active: bool
    active_block_count: int
    recovery_required: bool
    dominant_block_reason: str | None = None
    snapshot_id: str = field(default_factory=lambda: make_id("snapshot"))

    def __post_init__(self) -> None:
        object.__setattr__(self, "last_transition_at_utc", ensure_utc(self.last_transition_at_utc))

    @classmethod
    def create(
        cls,
        state_code: GlobalState,
        mode_code: OperationalMode,
        last_transition_event: str,
        readiness_class: ReadinessClass,
        integrity_class: IntegrityClass,
        kill_active: bool,
        active_block_count: int,
        recovery_required: bool,
        dominant_block_reason: str | None = None,
    ) -> "GlobalStateSnapshot":
        return cls(
            state_code=state_code,
            mode_code=mode_code,
            last_transition_event=last_transition_event,
            last_transition_at_utc=utc_now(),
            readiness_class=readiness_class,
            integrity_class=integrity_class,
            kill_active=kill_active,
            active_block_count=active_block_count,
            recovery_required=recovery_required,
            dominant_block_reason=dominant_block_reason,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "state_code": self.state_code.value,
            "mode_code": self.mode_code.value,
            "last_transition_event": self.last_transition_event,
            "last_transition_at_utc": isoformat_utc(self.last_transition_at_utc),
            "readiness_class": self.readiness_class.value,
            "integrity_class": self.integrity_class.value,
            "kill_active": self.kill_active,
            "active_block_count": self.active_block_count,
            "dominant_block_reason": self.dominant_block_reason,
            "recovery_required": self.recovery_required,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GlobalStateSnapshot":
        return cls(
            snapshot_id=data["snapshot_id"],
            state_code=GlobalState(data["state_code"]),
            mode_code=OperationalMode(data["mode_code"]),
            last_transition_event=data["last_transition_event"],
            last_transition_at_utc=parse_datetime(data["last_transition_at_utc"]) or utc_now(),
            readiness_class=ReadinessClass(data["readiness_class"]),
            integrity_class=IntegrityClass(data["integrity_class"]),
            kill_active=bool(data["kill_active"]),
            active_block_count=int(data["active_block_count"]),
            dominant_block_reason=data.get("dominant_block_reason"),
            recovery_required=bool(data["recovery_required"]),
        )


@dataclass(frozen=True, slots=True)
class CorePublicStateView:
    state_code: GlobalState
    mode_code: OperationalMode
    status_summary: str
    kill_active: bool
    active_block_vector: ActiveBlockVector
    readiness_class: ReadinessClass
    integrity_class: IntegrityClass
    last_transition: dict[str, str]
    critical_module_liveness: dict[str, str]
    dominant_block_reason: str | None = None
    health_metrics: dict[str, Any] = field(default_factory=dict)
    learn_state_view: LearnStateView | None = None

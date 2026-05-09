from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from shared.contracts_parts.core import CoreEventEnvelope
from shared.enums import (
    EventType,
    GlobalState,
    RecoveryConfidenceClass,
    RecoveryConsistencyGrade,
    RecoveryIncidentType,
    RecoveryResultCode,
    RecoveryState,
    Severity,
)
from shared.utils import ensure_utc, isoformat_utc, make_id, parse_datetime, utc_now


@dataclass(frozen=True, slots=True)
class RecoveryContext:
    incident_type: RecoveryIncidentType
    trigger_event_id: str
    recovery_mode: str
    recovery_id: str = field(default_factory=lambda: make_id("recovery"))
    started_at_utc: datetime = field(default_factory=utc_now)
    persisted_core_snapshot_ref: str | None = None
    persisted_block_vector_ref: str | None = None
    persisted_kill_flag_ref: str | None = None
    persisted_recovery_snapshot_ref: str | None = None
    current_observed_state_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "started_at_utc", ensure_utc(self.started_at_utc))
        if not self.trigger_event_id:
            raise ValueError("trigger_event_id is required")
        if not self.recovery_mode:
            raise ValueError("recovery_mode is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_id": self.recovery_id,
            "incident_type": self.incident_type.value,
            "trigger_event_id": self.trigger_event_id,
            "started_at_utc": isoformat_utc(self.started_at_utc),
            "persisted_core_snapshot_ref": self.persisted_core_snapshot_ref,
            "persisted_block_vector_ref": self.persisted_block_vector_ref,
            "persisted_kill_flag_ref": self.persisted_kill_flag_ref,
            "persisted_recovery_snapshot_ref": self.persisted_recovery_snapshot_ref,
            "current_observed_state_ref": self.current_observed_state_ref,
            "recovery_mode": self.recovery_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecoveryContext":
        return cls(
            recovery_id=data["recovery_id"],
            incident_type=RecoveryIncidentType(data["incident_type"]),
            trigger_event_id=data["trigger_event_id"],
            started_at_utc=parse_datetime(data["started_at_utc"]) or utc_now(),
            persisted_core_snapshot_ref=data.get("persisted_core_snapshot_ref"),
            persisted_block_vector_ref=data.get("persisted_block_vector_ref"),
            persisted_kill_flag_ref=data.get("persisted_kill_flag_ref"),
            persisted_recovery_snapshot_ref=data.get("persisted_recovery_snapshot_ref"),
            current_observed_state_ref=data.get("current_observed_state_ref"),
            recovery_mode=data["recovery_mode"],
        )


@dataclass(frozen=True, slots=True)
class ObservedStateSnapshot:
    module_availability_map: dict[str, bool]
    observed_snapshot_id: str = field(default_factory=lambda: make_id("observed"))
    collected_at_utc: datetime = field(default_factory=utc_now)
    core_runtime_marker_state: str | None = None
    market_state: str | None = None
    risk_state: str | None = None
    kill_active_observed: bool = False
    exec_state_summary: str | None = None
    last_known_intent_state: str | None = None
    heartbeat_health_summary: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "collected_at_utc", ensure_utc(self.collected_at_utc))
        if not self.module_availability_map:
            raise ValueError("module_availability_map is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_snapshot_id": self.observed_snapshot_id,
            "collected_at_utc": isoformat_utc(self.collected_at_utc),
            "core_runtime_marker_state": self.core_runtime_marker_state,
            "market_state": self.market_state,
            "risk_state": self.risk_state,
            "kill_active_observed": self.kill_active_observed,
            "exec_state_summary": self.exec_state_summary,
            "last_known_intent_state": self.last_known_intent_state,
            "heartbeat_health_summary": self.heartbeat_health_summary,
            "module_availability_map": self.module_availability_map,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObservedStateSnapshot":
        return cls(
            observed_snapshot_id=data["observed_snapshot_id"],
            collected_at_utc=parse_datetime(data["collected_at_utc"]) or utc_now(),
            core_runtime_marker_state=data.get("core_runtime_marker_state"),
            market_state=data.get("market_state"),
            risk_state=data.get("risk_state"),
            kill_active_observed=bool(data.get("kill_active_observed", False)),
            exec_state_summary=data.get("exec_state_summary"),
            last_known_intent_state=data.get("last_known_intent_state"),
            heartbeat_health_summary=dict(data.get("heartbeat_health_summary", {})),
            module_availability_map={str(key): bool(value) for key, value in data["module_availability_map"].items()},
        )


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    recovery_id: str
    is_consistent: bool
    consistency_grade: RecoveryConsistencyGrade
    conflicts_detected: tuple[str, ...]
    block_vector_consistency: str | None = None
    kill_consistency: str | None = None
    exec_consistency: str | None = None
    market_consistency: str | None = None
    notes: tuple[str, ...] = tuple()

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_id": self.recovery_id,
            "is_consistent": self.is_consistent,
            "consistency_grade": self.consistency_grade.value,
            "conflicts_detected": list(self.conflicts_detected),
            "block_vector_consistency": self.block_vector_consistency,
            "kill_consistency": self.kill_consistency,
            "exec_consistency": self.exec_consistency,
            "market_consistency": self.market_consistency,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReconciliationResult":
        return cls(
            recovery_id=data["recovery_id"],
            is_consistent=bool(data["is_consistent"]),
            consistency_grade=RecoveryConsistencyGrade(data["consistency_grade"]),
            conflicts_detected=tuple(data.get("conflicts_detected", [])),
            block_vector_consistency=data.get("block_vector_consistency"),
            kill_consistency=data.get("kill_consistency"),
            exec_consistency=data.get("exec_consistency"),
            market_consistency=data.get("market_consistency"),
            notes=tuple(data.get("notes", [])),
        )


@dataclass(frozen=True, slots=True)
class RecoveryConfidenceResult:
    recovery_id: str
    confidence_score: float
    confidence_class: RecoveryConfidenceClass
    missing_critical_evidence: tuple[str, ...]
    manual_intervention_recommended: bool
    safe_to_exit_recovery: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_id": self.recovery_id,
            "confidence_score": self.confidence_score,
            "confidence_class": self.confidence_class.value,
            "missing_critical_evidence": list(self.missing_critical_evidence),
            "manual_intervention_recommended": self.manual_intervention_recommended,
            "safe_to_exit_recovery": self.safe_to_exit_recovery,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecoveryConfidenceResult":
        return cls(
            recovery_id=data["recovery_id"],
            confidence_score=float(data["confidence_score"]),
            confidence_class=RecoveryConfidenceClass(data["confidence_class"]),
            missing_critical_evidence=tuple(data.get("missing_critical_evidence", [])),
            manual_intervention_recommended=bool(data["manual_intervention_recommended"]),
            safe_to_exit_recovery=bool(data["safe_to_exit_recovery"]),
        )


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    recovery_id: str
    result_code: RecoveryResultCode
    result_summary: str
    manual_intervention_required: bool
    block_vector_after_recovery: dict[str, Any]
    published_at_utc: datetime = field(default_factory=utc_now)
    target_post_recovery_state: GlobalState | None = None
    recovery_state: RecoveryState | None = None
    incident_type: RecoveryIncidentType | None = None
    reconciliation_confidence: float | None = None
    recovery_snapshot_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "published_at_utc", ensure_utc(self.published_at_utc))
        if not self.recovery_id:
            raise ValueError("recovery_id is required")
        if not self.result_summary:
            raise ValueError("result_summary is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_id": self.recovery_id,
            "recovery_state": self.recovery_state.value if self.recovery_state else None,
            "incident_type": self.incident_type.value if self.incident_type else None,
            "result_code": self.result_code.value,
            "recovery_result": self.result_code.value,
            "result_summary": self.result_summary,
            "target_post_recovery_state": self.target_post_recovery_state.value
            if self.target_post_recovery_state
            else None,
            "manual_intervention_required": self.manual_intervention_required,
            "block_vector_after_recovery": self.block_vector_after_recovery,
            "published_at_utc": isoformat_utc(self.published_at_utc),
            "reconciliation_confidence": self.reconciliation_confidence,
            "recovery_snapshot_ref": self.recovery_snapshot_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecoveryResult":
        target_state = data.get("target_post_recovery_state")
        recovery_state = data.get("recovery_state")
        incident_type = data.get("incident_type")
        return cls(
            recovery_id=data["recovery_id"],
            recovery_state=RecoveryState(recovery_state) if recovery_state else None,
            incident_type=RecoveryIncidentType(incident_type) if incident_type else None,
            result_code=RecoveryResultCode(data.get("result_code", data["recovery_result"])),
            result_summary=data["result_summary"],
            target_post_recovery_state=GlobalState(target_state) if target_state else None,
            manual_intervention_required=bool(data["manual_intervention_required"]),
            block_vector_after_recovery=dict(data["block_vector_after_recovery"]),
            published_at_utc=parse_datetime(data["published_at_utc"]) or utc_now(),
            reconciliation_confidence=float(data["reconciliation_confidence"])
            if data.get("reconciliation_confidence") is not None
            else None,
            recovery_snapshot_ref=data.get("recovery_snapshot_ref"),
        )

    @property
    def event_type(self) -> str:
        if self.result_code == RecoveryResultCode.VALIDATED:
            return EventType.RECOVERY_OK.value
        if self.result_code == RecoveryResultCode.VALIDATED_RESTRICTED:
            return EventType.RECOVERY_OK_RESTRICTED.value
        if self.result_code == RecoveryResultCode.MANUAL_REQUIRED:
            return EventType.RECOVERY_INTERVENTION_REQUIRED.value
        return EventType.RECOVERY_FAIL.value

    def to_core_payload(self) -> dict[str, Any]:
        return {
            "recovery_state": self.recovery_state.value if self.recovery_state else None,
            "incident_type": self.incident_type.value if self.incident_type else None,
            "recovery_result": self.result_code.value,
            "result_summary": self.result_summary,
            "manual_intervention_required": self.manual_intervention_required,
            "reconciliation_confidence": self.reconciliation_confidence,
            "recovery_snapshot_ref": self.recovery_snapshot_ref,
        }

    def to_core_event(self, source_module: str = "RECOVERY") -> CoreEventEnvelope:
        severity = Severity.INFO
        if self.result_code in {RecoveryResultCode.VALIDATED_RESTRICTED, RecoveryResultCode.INCONCLUSIVE}:
            severity = Severity.WARN
        if self.result_code in {RecoveryResultCode.FAILED, RecoveryResultCode.MANUAL_REQUIRED}:
            severity = Severity.ERROR
        return CoreEventEnvelope(
            event_type=self.event_type,
            source_module=source_module,
            severity=severity,
            payload=self.to_core_payload(),
        )


@dataclass(frozen=True, slots=True)
class RecoverySnapshot:
    context: RecoveryContext
    observed_state: ObservedStateSnapshot
    reconciliation: ReconciliationResult
    confidence: RecoveryConfidenceResult
    result: RecoveryResult
    recovery_snapshot_id: str = field(default_factory=lambda: make_id("recovery-snapshot"))
    created_at_utc: datetime = field(default_factory=utc_now)
    updated_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))
        object.__setattr__(self, "updated_at_utc", ensure_utc(self.updated_at_utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "recovery_snapshot_id": self.recovery_snapshot_id,
            "created_at_utc": isoformat_utc(self.created_at_utc),
            "updated_at_utc": isoformat_utc(self.updated_at_utc),
            "context": self.context.to_dict(),
            "observed_state": self.observed_state.to_dict(),
            "reconciliation": self.reconciliation.to_dict(),
            "confidence": self.confidence.to_dict(),
            "result": self.result.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecoverySnapshot":
        return cls(
            recovery_snapshot_id=data["recovery_snapshot_id"],
            created_at_utc=parse_datetime(data["created_at_utc"]) or utc_now(),
            updated_at_utc=parse_datetime(data["updated_at_utc"]) or utc_now(),
            context=RecoveryContext.from_dict(data["context"]),
            observed_state=ObservedStateSnapshot.from_dict(data["observed_state"]),
            reconciliation=ReconciliationResult.from_dict(data["reconciliation"]),
            confidence=RecoveryConfidenceResult.from_dict(data["confidence"]),
            result=RecoveryResult.from_dict(data["result"]),
        )

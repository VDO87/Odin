from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from shared.contracts_parts.core import CoreEventEnvelope
from shared.enums import (
    DecisionOutput,
    DecisionState,
    EventType,
    ExecutionFinalResult,
    ExecutionInitialResult,
    ExecutionState,
    GlobalState,
    OperationalMode,
    Severity,
)
from shared.utils import ensure_utc, isoformat_utc, make_id, parse_datetime, utc_now


@dataclass(frozen=True, slots=True)
class DecisionInputSnapshot:
    global_state: GlobalState
    current_mode: OperationalMode
    market_state: str
    context_class: str
    feed_integrity_state: str
    risk_state: str
    kill_active: bool
    active_block_vector_summary: dict[str, Any]
    instrument_snapshot_ref: str
    decision_config_version: str
    memory_advisory_context_ref: str | None = None
    memory_advisory_hash: str | None = None
    snapshot_id: str = field(default_factory=lambda: make_id("decision-snapshot"))
    created_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))
        if not self.market_state:
            raise ValueError("market_state is required")
        if not self.context_class:
            raise ValueError("context_class is required")
        if not self.feed_integrity_state:
            raise ValueError("feed_integrity_state is required")
        if not self.risk_state:
            raise ValueError("risk_state is required")
        if not self.instrument_snapshot_ref:
            raise ValueError("instrument_snapshot_ref is required")
        if not self.decision_config_version:
            raise ValueError("decision_config_version is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at_utc": isoformat_utc(self.created_at_utc),
            "global_state": self.global_state.value,
            "current_mode": self.current_mode.value,
            "market_state": self.market_state,
            "context_class": self.context_class,
            "feed_integrity_state": self.feed_integrity_state,
            "risk_state": self.risk_state,
            "kill_active": self.kill_active,
            "active_block_vector_summary": self.active_block_vector_summary,
            "instrument_snapshot_ref": self.instrument_snapshot_ref,
            "decision_config_version": self.decision_config_version,
            "memory_advisory_context_ref": self.memory_advisory_context_ref,
            "memory_advisory_hash": self.memory_advisory_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecisionInputSnapshot":
        return cls(
            snapshot_id=data["snapshot_id"],
            created_at_utc=parse_datetime(data["created_at_utc"]) or utc_now(),
            global_state=GlobalState(data["global_state"]),
            current_mode=OperationalMode(data["current_mode"]),
            market_state=data["market_state"],
            context_class=data["context_class"],
            feed_integrity_state=data["feed_integrity_state"],
            risk_state=data["risk_state"],
            kill_active=bool(data["kill_active"]),
            active_block_vector_summary=dict(data["active_block_vector_summary"]),
            instrument_snapshot_ref=data["instrument_snapshot_ref"],
            decision_config_version=data["decision_config_version"],
            memory_advisory_context_ref=data.get("memory_advisory_context_ref"),
            memory_advisory_hash=data.get("memory_advisory_hash"),
        )


@dataclass(frozen=True, slots=True)
class DecisionStateUpdate:
    decision_state: DecisionState
    decision_output: DecisionOutput
    reason_summary: str
    decision_cycle_id: str | None = None
    selected_tactic_id: str | None = None
    intent_id: str | None = None
    blocked_by_external: bool = False
    emitted_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "emitted_at_utc", ensure_utc(self.emitted_at_utc))
        if not self.reason_summary:
            raise ValueError("reason_summary is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_state": self.decision_state.value,
            "decision_output": self.decision_output.value,
            "decision_cycle_id": self.decision_cycle_id,
            "selected_tactic_id": self.selected_tactic_id,
            "intent_id": self.intent_id,
            "blocked_by_external": self.blocked_by_external,
            "reason_summary": self.reason_summary,
            "emitted_at_utc": isoformat_utc(self.emitted_at_utc),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecisionStateUpdate":
        return cls(
            decision_state=DecisionState(data["decision_state"]),
            decision_output=DecisionOutput(data["decision_output"]),
            reason_summary=data["reason_summary"],
            decision_cycle_id=data.get("decision_cycle_id"),
            selected_tactic_id=data.get("selected_tactic_id"),
            intent_id=data.get("intent_id"),
            blocked_by_external=bool(data.get("blocked_by_external", False)),
            emitted_at_utc=parse_datetime(data.get("emitted_at_utc")) or utc_now(),
        )

    def to_core_payload(self) -> dict[str, Any]:
        return self.to_dict()

    @property
    def event_type(self) -> str:
        if self.decision_state == DecisionState.DECISION_ERROR or self.decision_output == DecisionOutput.ERROR:
            return EventType.DECISION_ERROR.value
        return EventType.DECISION_STATE_UPDATE.value

    def to_core_event(self, source_module: str = "DECISION") -> CoreEventEnvelope:
        severity = Severity.INFO
        if self.decision_output in {DecisionOutput.RESTRICTED, DecisionOutput.WAIT}:
            severity = Severity.WARN
        if self.decision_output in {DecisionOutput.BLOCKED, DecisionOutput.ERROR}:
            severity = Severity.ERROR
        return CoreEventEnvelope(
            event_type=self.event_type,
            source_module=source_module,
            severity=severity,
            payload=self.to_core_payload(),
        )


@dataclass(frozen=True, slots=True)
class DecisionCycleResult:
    decision_cycle_id: str
    snapshot_id: str
    decision_state: DecisionState
    decision_output: DecisionOutput
    intent_emitted: bool
    blocked_by_external: bool
    reason_summary: str
    winner_hypothesis_id: str | None = None
    selected_tactic_id: str | None = None
    intent_id: str | None = None
    generated_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "generated_at_utc", ensure_utc(self.generated_at_utc))
        if not self.decision_cycle_id:
            raise ValueError("decision_cycle_id is required")
        if not self.snapshot_id:
            raise ValueError("snapshot_id is required")
        if not self.reason_summary:
            raise ValueError("reason_summary is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_cycle_id": self.decision_cycle_id,
            "snapshot_id": self.snapshot_id,
            "decision_state": self.decision_state.value,
            "decision_output": self.decision_output.value,
            "winner_hypothesis_id": self.winner_hypothesis_id,
            "selected_tactic_id": self.selected_tactic_id,
            "intent_id": self.intent_id,
            "intent_emitted": self.intent_emitted,
            "blocked_by_external": self.blocked_by_external,
            "reason_summary": self.reason_summary,
            "generated_at_utc": isoformat_utc(self.generated_at_utc),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecisionCycleResult":
        return cls(
            decision_cycle_id=data["decision_cycle_id"],
            snapshot_id=data["snapshot_id"],
            decision_state=DecisionState(data["decision_state"]),
            decision_output=DecisionOutput(data["decision_output"]),
            winner_hypothesis_id=data.get("winner_hypothesis_id"),
            selected_tactic_id=data.get("selected_tactic_id"),
            intent_id=data.get("intent_id"),
            intent_emitted=bool(data["intent_emitted"]),
            blocked_by_external=bool(data["blocked_by_external"]),
            reason_summary=data["reason_summary"],
            generated_at_utc=parse_datetime(data["generated_at_utc"]) or utc_now(),
        )

    def to_state_update(self) -> DecisionStateUpdate:
        return DecisionStateUpdate(
            decision_state=self.decision_state,
            decision_output=self.decision_output,
            reason_summary=self.reason_summary,
            decision_cycle_id=self.decision_cycle_id,
            selected_tactic_id=self.selected_tactic_id,
            intent_id=self.intent_id,
            blocked_by_external=self.blocked_by_external,
            emitted_at_utc=self.generated_at_utc,
        )

    def to_core_event(self, source_module: str = "DECISION") -> CoreEventEnvelope:
        state_update = self.to_state_update()
        event_type = EventType.DECISION_CYCLE_CLOSED.value
        if state_update.event_type == EventType.DECISION_ERROR.value:
            event_type = EventType.DECISION_ERROR.value
        severity = Severity.INFO
        if self.decision_output in {DecisionOutput.RESTRICTED, DecisionOutput.WAIT}:
            severity = Severity.WARN
        if self.decision_output in {DecisionOutput.BLOCKED, DecisionOutput.ERROR}:
            severity = Severity.ERROR
        return CoreEventEnvelope(
            event_type=event_type,
            source_module=source_module,
            severity=severity,
            payload=self.to_state_update().to_core_payload(),
        )


@dataclass(frozen=True, slots=True)
class ExecutionIntent:
    intent_id: str
    decision_cycle_id: str
    created_at_utc: datetime
    ttl_ms: int
    expires_at_utc: datetime
    instrument_id: str
    side: str
    target_order_type: str
    max_slippage: float
    market_snapshot_ref: str
    risk_snapshot_ref: str
    hypothesis_id: str | None = None
    tactic_id: str | None = None
    price_reference: float | None = None
    decision_config_version: str | None = None
    decision_version: str | None = None
    reason_summary: str | None = None
    intent_direction: str | None = None
    restriction_flags: tuple[str, ...] = tuple()
    rationale_ref: str | None = None
    memory_advisory_context_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))
        object.__setattr__(self, "expires_at_utc", ensure_utc(self.expires_at_utc))
        if not self.intent_id:
            raise ValueError("intent_id is required")
        if not self.decision_cycle_id:
            raise ValueError("decision_cycle_id is required")
        if self.ttl_ms <= 0:
            raise ValueError("ttl_ms must be > 0")
        if self.expires_at_utc <= self.created_at_utc:
            raise ValueError("expires_at_utc must be greater than created_at_utc")
        if not self.instrument_id:
            raise ValueError("instrument_id is required")
        if not self.side:
            raise ValueError("side is required")
        if not self.target_order_type:
            raise ValueError("target_order_type is required")
        if not self.market_snapshot_ref:
            raise ValueError("market_snapshot_ref is required")
        if not self.risk_snapshot_ref:
            raise ValueError("risk_snapshot_ref is required")

    @classmethod
    def create(
        cls,
        *,
        intent_id: str,
        decision_cycle_id: str,
        ttl_ms: int,
        instrument_id: str,
        side: str,
        target_order_type: str,
        max_slippage: float,
        market_snapshot_ref: str,
        risk_snapshot_ref: str,
        created_at_utc: datetime | None = None,
        hypothesis_id: str | None = None,
        tactic_id: str | None = None,
        price_reference: float | None = None,
        decision_config_version: str | None = None,
        decision_version: str | None = None,
        reason_summary: str | None = None,
        intent_direction: str | None = None,
        restriction_flags: tuple[str, ...] = tuple(),
        rationale_ref: str | None = None,
        memory_advisory_context_ref: str | None = None,
    ) -> "ExecutionIntent":
        created = ensure_utc(created_at_utc or utc_now())
        expires = created + timedelta(milliseconds=ttl_ms)
        return cls(
            intent_id=intent_id,
            decision_cycle_id=decision_cycle_id,
            created_at_utc=created,
            ttl_ms=ttl_ms,
            expires_at_utc=expires,
            instrument_id=instrument_id,
            side=side,
            target_order_type=target_order_type,
            max_slippage=max_slippage,
            market_snapshot_ref=market_snapshot_ref,
            risk_snapshot_ref=risk_snapshot_ref,
            hypothesis_id=hypothesis_id,
            tactic_id=tactic_id,
            price_reference=price_reference,
            decision_config_version=decision_config_version,
            decision_version=decision_version,
            reason_summary=reason_summary,
            intent_direction=intent_direction,
            restriction_flags=restriction_flags,
            rationale_ref=rationale_ref,
            memory_advisory_context_ref=memory_advisory_context_ref,
        )

    def to_dict(self) -> dict[str, Any]:
        decision_version = self.decision_version or self.decision_config_version
        direction = self.intent_direction or self.side
        restrictions = list(self.restriction_flags)
        return {
            "intent_id": self.intent_id,
            "decision_cycle_id": self.decision_cycle_id,
            "created_at_utc": isoformat_utc(self.created_at_utc),
            "ttl_ms": self.ttl_ms,
            "expires_at_utc": isoformat_utc(self.expires_at_utc),
            "instrument_id": self.instrument_id,
            "side": self.side,
            "target_order_type": self.target_order_type,
            "price_reference": self.price_reference,
            "max_slippage": self.max_slippage,
            "market_snapshot_ref": self.market_snapshot_ref,
            "risk_snapshot_ref": self.risk_snapshot_ref,
            "hypothesis_id": self.hypothesis_id,
            "tactic_id": self.tactic_id,
            "decision_config_version": self.decision_config_version or decision_version,
            "decision_version": decision_version,
            "reason_summary": self.reason_summary,
            "intent_direction": direction,
            "restriction_flags": restrictions,
            "restrictions": restrictions,
            "rationale_ref": self.rationale_ref,
            "memory_advisory_context_ref": self.memory_advisory_context_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionIntent":
        return cls(
            intent_id=data["intent_id"],
            decision_cycle_id=data["decision_cycle_id"],
            created_at_utc=parse_datetime(data["created_at_utc"]) or utc_now(),
            ttl_ms=int(data["ttl_ms"]),
            expires_at_utc=parse_datetime(data["expires_at_utc"]) or utc_now(),
            instrument_id=data["instrument_id"],
            side=data["side"],
            target_order_type=data["target_order_type"],
            max_slippage=float(data["max_slippage"]),
            market_snapshot_ref=data["market_snapshot_ref"],
            risk_snapshot_ref=data["risk_snapshot_ref"],
            hypothesis_id=data.get("hypothesis_id"),
            tactic_id=data.get("tactic_id"),
            price_reference=data.get("price_reference"),
            decision_config_version=data.get("decision_config_version"),
            decision_version=data.get("decision_version"),
            reason_summary=data.get("reason_summary"),
            intent_direction=data.get("intent_direction"),
            restriction_flags=tuple(data.get("restriction_flags", data.get("restrictions", []))),
            rationale_ref=data.get("rationale_ref"),
            memory_advisory_context_ref=data.get("memory_advisory_context_ref"),
        )


OperationalIntent = ExecutionIntent


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    intent_id: str
    decision_cycle_id: str
    status: str
    first_seen_at_utc: datetime
    last_update_at_utc: datetime
    submission_ref: str | None = None
    result_state: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "first_seen_at_utc", ensure_utc(self.first_seen_at_utc))
        object.__setattr__(self, "last_update_at_utc", ensure_utc(self.last_update_at_utc))
        if not self.intent_id:
            raise ValueError("intent_id is required")
        if not self.decision_cycle_id:
            raise ValueError("decision_cycle_id is required")
        if not self.status:
            raise ValueError("status is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "decision_cycle_id": self.decision_cycle_id,
            "status": self.status,
            "first_seen_at_utc": isoformat_utc(self.first_seen_at_utc),
            "last_update_at_utc": isoformat_utc(self.last_update_at_utc),
            "submission_ref": self.submission_ref,
            "result_state": self.result_state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IdempotencyRecord":
        return cls(
            intent_id=data["intent_id"],
            decision_cycle_id=data["decision_cycle_id"],
            status=data["status"],
            first_seen_at_utc=parse_datetime(data["first_seen_at_utc"]) or utc_now(),
            last_update_at_utc=parse_datetime(data["last_update_at_utc"]) or utc_now(),
            submission_ref=data.get("submission_ref"),
            result_state=data.get("result_state"),
        )


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    request_id: str
    intent_id: str
    instrument_id: str
    side: str
    target_order_type: str
    max_slippage: float
    created_at_utc: datetime
    price_reference: float | None = None
    routing_context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))
        if not self.request_id:
            raise ValueError("request_id is required")
        if not self.intent_id:
            raise ValueError("intent_id is required")
        if not self.instrument_id:
            raise ValueError("instrument_id is required")
        if not self.side:
            raise ValueError("side is required")
        if not self.target_order_type:
            raise ValueError("target_order_type is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "intent_id": self.intent_id,
            "instrument_id": self.instrument_id,
            "side": self.side,
            "target_order_type": self.target_order_type,
            "price_reference": self.price_reference,
            "max_slippage": self.max_slippage,
            "created_at_utc": isoformat_utc(self.created_at_utc),
            "routing_context": self.routing_context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionRequest":
        return cls(
            request_id=data["request_id"],
            intent_id=data["intent_id"],
            instrument_id=data["instrument_id"],
            side=data["side"],
            target_order_type=data["target_order_type"],
            price_reference=data.get("price_reference"),
            max_slippage=float(data["max_slippage"]),
            created_at_utc=parse_datetime(data["created_at_utc"]) or utc_now(),
            routing_context=dict(data.get("routing_context", {})),
        )


@dataclass(frozen=True, slots=True)
class ExecutionStateUpdate:
    exec_state: ExecutionState
    divergence_flag: bool
    intent_id: str | None = None
    decision_cycle_id: str | None = None
    request_id: str | None = None
    initial_result: ExecutionInitialResult | None = None
    final_result: ExecutionFinalResult | None = None
    reason_summary: str | None = None
    slippage_value: float | None = None
    divergence_class: str | None = None
    reconciliation_confidence: float | None = None
    emitted_at_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "emitted_at_utc", ensure_utc(self.emitted_at_utc))

    def to_dict(self) -> dict[str, Any]:
        execution_result = None
        if self.final_result is not None:
            execution_result = self.final_result.value
        elif self.initial_result is not None:
            execution_result = self.initial_result.value
        return {
            "execution_state": self.exec_state.value,
            "exec_state": self.exec_state.value,
            "intent_id": self.intent_id,
            "decision_cycle_id": self.decision_cycle_id,
            "request_id": self.request_id,
            "execution_result": execution_result,
            "initial_result": self.initial_result.value if self.initial_result else None,
            "final_result": self.final_result.value if self.final_result else None,
            "divergence_flag": self.divergence_flag,
            "reason_code": self.reason_summary,
            "reason_summary": self.reason_summary,
            "slippage_value": self.slippage_value,
            "divergence_class": self.divergence_class,
            "reconciliation_confidence": self.reconciliation_confidence,
            "emitted_at_utc": isoformat_utc(self.emitted_at_utc),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionStateUpdate":
        exec_state_value = data.get("exec_state", data.get("execution_state"))
        if exec_state_value is None:
            raise ValueError("exec_state or execution_state is required")
        return cls(
            exec_state=ExecutionState(exec_state_value),
            divergence_flag=bool(data["divergence_flag"]),
            intent_id=data.get("intent_id"),
            decision_cycle_id=data.get("decision_cycle_id"),
            request_id=data.get("request_id"),
            initial_result=ExecutionInitialResult(data["initial_result"])
            if data.get("initial_result")
            else None,
            final_result=ExecutionFinalResult(data["final_result"]) if data.get("final_result") else None,
            reason_summary=data.get("reason_summary"),
            slippage_value=float(data["slippage_value"]) if data.get("slippage_value") is not None else None,
            divergence_class=data.get("divergence_class"),
            reconciliation_confidence=float(data["reconciliation_confidence"])
            if data.get("reconciliation_confidence") is not None
            else None,
            emitted_at_utc=parse_datetime(data.get("emitted_at_utc")) or utc_now(),
        )

    def to_core_payload(self) -> dict[str, Any]:
        return self.to_dict()

    @property
    def event_type(self) -> str:
        if self.exec_state == ExecutionState.CANCELLED_EXPIRED:
            return EventType.INTENTION_EXPIRED.value
        if self.divergence_flag or self.final_result == ExecutionFinalResult.CRITICAL_DIVERGENCE:
            return EventType.EXEC_DIVERGENCE.value
        if self.exec_state == ExecutionState.EXECUTION_CONFIRMED:
            return EventType.EXEC_CONFIRMED.value
        if self.exec_state in {ExecutionState.SUBMITTED, ExecutionState.PENDING_CONFIRMATION}:
            return EventType.EXEC_SUBMITTED.value
        if self.exec_state in {ExecutionState.REJECTED, ExecutionState.FAILED}:
            if self.slippage_value is not None:
                return EventType.EXEC_REJECTED_SLIPPAGE.value
            return EventType.EXEC_REJECTED.value
        return EventType.EXEC_SUBMITTED.value

    def to_core_event(self, source_module: str = "EXEC") -> CoreEventEnvelope:
        severity = Severity.INFO
        if self.event_type in {EventType.INTENTION_EXPIRED.value, EventType.EXEC_REJECTED_SLIPPAGE.value}:
            severity = Severity.WARN
        if self.event_type in {EventType.EXEC_REJECTED.value, EventType.EXEC_DIVERGENCE.value}:
            severity = Severity.ERROR
        return CoreEventEnvelope(
            event_type=self.event_type,
            source_module=source_module,
            severity=severity,
            payload=self.to_core_payload(),
        )


@dataclass(frozen=True, slots=True)
class ExecutionSnapshot:
    intent_id: str
    exec_state: ExecutionState
    created_at_utc: datetime
    updated_at_utc: datetime
    divergence_flag: bool
    execution_snapshot_id: str = field(default_factory=lambda: make_id("exec-snapshot"))
    request_id: str | None = None
    decision_cycle_id: str | None = None
    initial_result: ExecutionInitialResult | None = None
    final_result: ExecutionFinalResult | None = None
    reason_summary: str | None = None
    divergence_class: str | None = None
    slippage_value: float | None = None
    reconciliation_confidence: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))
        object.__setattr__(self, "updated_at_utc", ensure_utc(self.updated_at_utc))
        if not self.intent_id:
            raise ValueError("intent_id is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_snapshot_id": self.execution_snapshot_id,
            "intent_id": self.intent_id,
            "request_id": self.request_id,
            "decision_cycle_id": self.decision_cycle_id,
            "exec_state": self.exec_state.value,
            "execution_state": self.exec_state.value,
            "initial_result": self.initial_result.value if self.initial_result else None,
            "final_result": self.final_result.value if self.final_result else None,
            "created_at_utc": isoformat_utc(self.created_at_utc),
            "updated_at_utc": isoformat_utc(self.updated_at_utc),
            "divergence_flag": self.divergence_flag,
            "divergence_class": self.divergence_class,
            "slippage_value": self.slippage_value,
            "reconciliation_confidence": self.reconciliation_confidence,
            "reason_summary": self.reason_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionSnapshot":
        exec_state_value = data.get("exec_state", data.get("execution_state"))
        if exec_state_value is None:
            raise ValueError("exec_state or execution_state is required")
        return cls(
            execution_snapshot_id=data["execution_snapshot_id"],
            intent_id=data["intent_id"],
            request_id=data.get("request_id"),
            decision_cycle_id=data.get("decision_cycle_id"),
            exec_state=ExecutionState(exec_state_value),
            initial_result=ExecutionInitialResult(data["initial_result"])
            if data.get("initial_result")
            else None,
            final_result=ExecutionFinalResult(data["final_result"]) if data.get("final_result") else None,
            created_at_utc=parse_datetime(data["created_at_utc"]) or utc_now(),
            updated_at_utc=parse_datetime(data["updated_at_utc"]) or utc_now(),
            divergence_flag=bool(data["divergence_flag"]),
            divergence_class=data.get("divergence_class"),
            slippage_value=float(data["slippage_value"]) if data.get("slippage_value") is not None else None,
            reconciliation_confidence=float(data["reconciliation_confidence"])
            if data.get("reconciliation_confidence") is not None
            else None,
            reason_summary=data.get("reason_summary"),
        )

    def to_state_update(self) -> ExecutionStateUpdate:
        return ExecutionStateUpdate(
            exec_state=self.exec_state,
            divergence_flag=self.divergence_flag,
            intent_id=self.intent_id,
            decision_cycle_id=self.decision_cycle_id,
            request_id=self.request_id,
            initial_result=self.initial_result,
            final_result=self.final_result,
            reason_summary=self.reason_summary,
            slippage_value=self.slippage_value,
            divergence_class=self.divergence_class,
            reconciliation_confidence=self.reconciliation_confidence,
            emitted_at_utc=self.updated_at_utc,
        )


@dataclass(frozen=True, slots=True)
class ExecutionLedgerRecord:
    intent_id: str
    decision_cycle_id: str
    execution_mode: OperationalMode
    global_state: GlobalState
    risk_decision: str
    market_state: str
    market_readiness: str
    exec_state: ExecutionState
    recorded_at_utc: datetime
    ledger_id: str = field(default_factory=lambda: make_id("exec-ledger"))
    request_id: str | None = None
    initial_result: ExecutionInitialResult | None = None
    final_result: ExecutionFinalResult | None = None
    reason_summary: str | None = None
    slippage_value: float | None = None
    adapter_name: str | None = None
    external_order_ref: str | None = None
    audit_ref: str | None = None
    was_deduplicated: bool = False
    request_payload: dict[str, Any] = field(default_factory=dict)
    snapshot_payload: dict[str, Any] = field(default_factory=dict)
    idempotency_payload: dict[str, Any] = field(default_factory=dict)
    transport_payload: dict[str, Any] = field(default_factory=dict)
    context_payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "recorded_at_utc", ensure_utc(self.recorded_at_utc))
        if not self.intent_id:
            raise ValueError("intent_id is required")
        if not self.decision_cycle_id:
            raise ValueError("decision_cycle_id is required")
        if not self.risk_decision:
            raise ValueError("risk_decision is required")
        if not self.market_state:
            raise ValueError("market_state is required")
        if not self.market_readiness:
            raise ValueError("market_readiness is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "intent_id": self.intent_id,
            "decision_cycle_id": self.decision_cycle_id,
            "execution_mode": self.execution_mode.value,
            "global_state": self.global_state.value,
            "risk_decision": self.risk_decision,
            "market_state": self.market_state,
            "market_readiness": self.market_readiness,
            "exec_state": self.exec_state.value,
            "request_id": self.request_id,
            "initial_result": self.initial_result.value if self.initial_result else None,
            "final_result": self.final_result.value if self.final_result else None,
            "reason_summary": self.reason_summary,
            "slippage_value": self.slippage_value,
            "adapter_name": self.adapter_name,
            "external_order_ref": self.external_order_ref,
            "audit_ref": self.audit_ref,
            "was_deduplicated": self.was_deduplicated,
            "recorded_at_utc": isoformat_utc(self.recorded_at_utc),
            "request_payload": self.request_payload,
            "snapshot_payload": self.snapshot_payload,
            "idempotency_payload": self.idempotency_payload,
            "transport_payload": self.transport_payload,
            "context_payload": self.context_payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionLedgerRecord":
        return cls(
            ledger_id=data["ledger_id"],
            intent_id=data["intent_id"],
            decision_cycle_id=data["decision_cycle_id"],
            execution_mode=OperationalMode(data["execution_mode"]),
            global_state=GlobalState(data["global_state"]),
            risk_decision=data["risk_decision"],
            market_state=data["market_state"],
            market_readiness=data["market_readiness"],
            exec_state=ExecutionState(data["exec_state"]),
            request_id=data.get("request_id"),
            initial_result=ExecutionInitialResult(data["initial_result"])
            if data.get("initial_result")
            else None,
            final_result=ExecutionFinalResult(data["final_result"]) if data.get("final_result") else None,
            reason_summary=data.get("reason_summary"),
            slippage_value=float(data["slippage_value"]) if data.get("slippage_value") is not None else None,
            adapter_name=data.get("adapter_name"),
            external_order_ref=data.get("external_order_ref"),
            audit_ref=data.get("audit_ref"),
            was_deduplicated=bool(data.get("was_deduplicated", False)),
            recorded_at_utc=parse_datetime(data["recorded_at_utc"]) or utc_now(),
            request_payload=dict(data.get("request_payload", {})),
            snapshot_payload=dict(data.get("snapshot_payload", {})),
            idempotency_payload=dict(data.get("idempotency_payload", {})),
            transport_payload=dict(data.get("transport_payload", {})),
            context_payload=dict(data.get("context_payload", {})),
        )

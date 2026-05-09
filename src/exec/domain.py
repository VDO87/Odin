from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
import json
from pathlib import Path
from typing import Any, Protocol

from shared.contracts import (
    ExecutionLedgerRecord,
    ExecutionIntent,
    ExecutionRequest,
    ExecutionSnapshot,
    ExecutionStateUpdate,
    IdempotencyRecord,
)
from shared.enums import (
    ExecutionFinalResult,
    ExecutionInitialResult,
    ExecutionState,
    GlobalState,
    OperationalMode,
)
from shared.utils import ensure_utc, make_id, utc_now


FINAL_EXEC_STATES = {
    ExecutionState.EXECUTION_CONFIRMED,
    ExecutionState.REJECTED,
    ExecutionState.FAILED,
    ExecutionState.DIVERGENT,
    ExecutionState.CANCELLED_EXPIRED,
}


class TransportSubmissionStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass(frozen=True, slots=True)
class TransportSubmissionResult:
    adapter_name: str
    transport_status: TransportSubmissionStatus
    observed_at_utc: datetime = field(default_factory=utc_now)
    external_order_ref: str | None = None
    accepted_price: float | None = None
    reason_summary: str | None = None
    transport_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at_utc", ensure_utc(self.observed_at_utc))
        if not self.adapter_name:
            raise ValueError("adapter_name is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "transport_status": self.transport_status.value,
            "observed_at_utc": self.observed_at_utc.isoformat(),
            "external_order_ref": self.external_order_ref,
            "accepted_price": self.accepted_price,
            "reason_summary": self.reason_summary,
            "transport_metadata": self.transport_metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TransportSubmissionResult":
        return cls(
            adapter_name=data["adapter_name"],
            transport_status=TransportSubmissionStatus(data["transport_status"]),
            observed_at_utc=datetime.fromisoformat(data["observed_at_utc"]),
            external_order_ref=data.get("external_order_ref"),
            accepted_price=float(data["accepted_price"])
            if data.get("accepted_price") is not None
            else None,
            reason_summary=data.get("reason_summary"),
            transport_metadata=dict(data.get("transport_metadata", {})),
        )


class ExecutionTransportAdapter(Protocol):
    adapter_name: str

    def submit(self, request: ExecutionRequest) -> TransportSubmissionResult: ...


class ExecutionLedgerWriter(Protocol):
    def write_execution_ledger_record(self, record: ExecutionLedgerRecord) -> None: ...


@dataclass(frozen=True, slots=True)
class RealExecutionAuditRecord:
    intent_id: str
    request_id: str
    adapter_name: str
    operator_approval_ref: str
    approved_by: str
    change_ticket: str
    transport_status: str
    reason_summary: str
    audit_id: str = field(default_factory=lambda: make_id("real-audit"))
    created_at_utc: datetime = field(default_factory=utc_now)
    external_order_ref: str | None = None
    request_payload: dict[str, Any] = field(default_factory=dict)
    transport_payload: dict[str, Any] = field(default_factory=dict)
    snapshot_payload: dict[str, Any] = field(default_factory=dict)
    idempotency_payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at_utc", ensure_utc(self.created_at_utc))
        if not self.intent_id:
            raise ValueError("intent_id is required")
        if not self.request_id:
            raise ValueError("request_id is required")
        if not self.adapter_name:
            raise ValueError("adapter_name is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "intent_id": self.intent_id,
            "request_id": self.request_id,
            "adapter_name": self.adapter_name,
            "operator_approval_ref": self.operator_approval_ref,
            "approved_by": self.approved_by,
            "change_ticket": self.change_ticket,
            "transport_status": self.transport_status,
            "reason_summary": self.reason_summary,
            "created_at_utc": self.created_at_utc.isoformat(),
            "external_order_ref": self.external_order_ref,
            "request_payload": self.request_payload,
            "transport_payload": self.transport_payload,
            "snapshot_payload": self.snapshot_payload,
            "idempotency_payload": self.idempotency_payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RealExecutionAuditRecord":
        return cls(
            audit_id=data["audit_id"],
            intent_id=data["intent_id"],
            request_id=data["request_id"],
            adapter_name=data["adapter_name"],
            operator_approval_ref=data["operator_approval_ref"],
            approved_by=data["approved_by"],
            change_ticket=data["change_ticket"],
            transport_status=data["transport_status"],
            reason_summary=data["reason_summary"],
            created_at_utc=datetime.fromisoformat(data["created_at_utc"]),
            external_order_ref=data.get("external_order_ref"),
            request_payload=dict(data.get("request_payload", {})),
            transport_payload=dict(data.get("transport_payload", {})),
            snapshot_payload=dict(data.get("snapshot_payload", {})),
            idempotency_payload=dict(data.get("idempotency_payload", {})),
        )


@dataclass(frozen=True, slots=True)
class PreExecutionContext:
    global_state: GlobalState
    current_mode: OperationalMode
    risk_decision: str
    market_state: str
    market_readiness: str
    kill_active: bool = False
    active_block_count: int = 0
    channel_healthy: bool = True
    current_executable_price: float | None = None
    confirmed_price: float | None = None
    routing_context: dict[str, Any] = field(default_factory=dict)
    now_utc: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "now_utc", ensure_utc(self.now_utc))


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    snapshot: ExecutionSnapshot
    state_update: ExecutionStateUpdate
    core_event_type: str
    idempotency_record: IdempotencyRecord
    request: ExecutionRequest | None = None
    was_deduplicated: bool = False

    def to_core_event(self):
        return self.state_update.to_core_event()


class DemoExecutionEngine:
    def __init__(self, *, ledger_store: ExecutionLedgerWriter | None = None) -> None:
        self._records: dict[str, IdempotencyRecord] = {}
        self._snapshots: dict[str, ExecutionSnapshot] = {}
        self._ledger_store = ledger_store

    def execute(self, intent: ExecutionIntent, context: PreExecutionContext) -> ExecutionReport:
        existing_snapshot = self._snapshots.get(intent.intent_id)
        if existing_snapshot is not None and existing_snapshot.exec_state in FINAL_EXEC_STATES:
            state_update = existing_snapshot.to_state_update()
            record = self._records[intent.intent_id]
            return self._return_report(
                intent,
                context,
                ExecutionReport(
                    snapshot=existing_snapshot,
                    state_update=state_update,
                    core_event_type=state_update.event_type,
                    idempotency_record=record,
                    was_deduplicated=True,
                ),
            )

        rejection_reason = self._precheck_rejection(intent, context)
        if rejection_reason is not None:
            return self._return_report(
                intent,
                context,
                self._finalize_without_submission(
                    intent,
                    context,
                    exec_state=ExecutionState.REJECTED,
                    initial_result=ExecutionInitialResult.REJECTED,
                    final_result=ExecutionFinalResult.CONFIRMED_REJECTED,
                    reason_summary=rejection_reason,
                ),
            )

        if self._is_expired(intent, context.now_utc):
            return self._return_report(
                intent,
                context,
                self._finalize_without_submission(
                    intent,
                    context,
                    exec_state=ExecutionState.CANCELLED_EXPIRED,
                    initial_result=None,
                    final_result=ExecutionFinalResult.CANCELLED_EXPIRED,
                    reason_summary="intent_expired",
                ),
            )

        request = ExecutionRequest(
            request_id=make_id("request"),
            intent_id=intent.intent_id,
            instrument_id=intent.instrument_id,
            side=intent.side,
            target_order_type=intent.target_order_type,
            price_reference=intent.price_reference,
            max_slippage=float(intent.max_slippage),
            created_at_utc=context.now_utc,
            routing_context=dict(context.routing_context),
        )

        preventive_slippage = self._slippage_value(intent.price_reference, context.current_executable_price)
        if preventive_slippage is None and intent.price_reference is None:
            return self._return_report(
                intent,
                context,
                self._finalize_without_submission(
                    intent,
                    context,
                    exec_state=ExecutionState.REJECTED,
                    initial_result=ExecutionInitialResult.REJECTED,
                    final_result=ExecutionFinalResult.CONFIRMED_REJECTED,
                    reason_summary="missing_price_reference",
                ),
            )
        if preventive_slippage is not None and preventive_slippage > float(intent.max_slippage):
            return self._return_report(
                intent,
                context,
                self._finalize_without_submission(
                    intent,
                    context,
                    exec_state=ExecutionState.REJECTED,
                    initial_result=ExecutionInitialResult.REJECTED,
                    final_result=ExecutionFinalResult.CONFIRMED_REJECTED,
                    reason_summary="slippage_rejected_pre_submission",
                    request=request,
                    slippage_value=preventive_slippage,
                ),
            )

        confirmed_price = context.confirmed_price
        if confirmed_price is None:
            confirmed_price = context.current_executable_price
        if confirmed_price is None:
            confirmed_price = intent.price_reference

        confirmed_slippage = self._slippage_value(intent.price_reference, confirmed_price)
        if confirmed_slippage is not None and confirmed_slippage > float(intent.max_slippage):
            return self._return_report(
                intent,
                context,
                self._finalize_without_submission(
                    intent,
                    context,
                    exec_state=ExecutionState.DIVERGENT,
                    initial_result=ExecutionInitialResult.ACCEPTED,
                    final_result=ExecutionFinalResult.CRITICAL_DIVERGENCE,
                    reason_summary="slippage_divergence_post_submission",
                    request=request,
                    divergence_flag=True,
                    divergence_class="slippage_exceeded_after_submission",
                    slippage_value=confirmed_slippage,
                ),
            )

        snapshot = ExecutionSnapshot(
            intent_id=intent.intent_id,
            decision_cycle_id=intent.decision_cycle_id,
            request_id=request.request_id,
            exec_state=ExecutionState.EXECUTION_CONFIRMED,
            initial_result=ExecutionInitialResult.ACCEPTED,
            final_result=ExecutionFinalResult.CONFIRMED_EXECUTED,
            created_at_utc=context.now_utc,
            updated_at_utc=context.now_utc,
            divergence_flag=False,
            slippage_value=confirmed_slippage,
            reason_summary="demo_execution_confirmed",
        )
        return self._return_report(intent, context, self._finalize(intent, snapshot, request=request))

    def _precheck_rejection(self, intent: ExecutionIntent, context: PreExecutionContext) -> str | None:
        if context.current_mode != OperationalMode.DEMO:
            return "mode_incompatible_for_demo_exec"
        if context.global_state not in {GlobalState.READY, GlobalState.ACTIVE}:
            return "global_state_incompatible"
        if context.kill_active:
            return "kill_active"
        if context.active_block_count > 0:
            return "active_block_present"
        if context.risk_decision in {"BLOCK", "KILL"}:
            return "risk_blocks_execution"
        if context.market_state in {"MS-30", "MS-40", "MS-50"}:
            return "market_incompatible"
        if context.market_readiness in {"NOT_READY", "UNAVAILABLE"}:
            return "market_not_ready"
        if not context.channel_healthy:
            return "execution_channel_unhealthy"
        if not intent.intent_id:
            return "intent_invalid"
        return None

    def _is_expired(self, intent: ExecutionIntent, now_utc: datetime) -> bool:
        now_value = ensure_utc(now_utc)
        elapsed_ms = int((now_value - intent.created_at_utc).total_seconds() * 1000)
        return now_value > intent.expires_at_utc or elapsed_ms > intent.ttl_ms

    def _slippage_value(self, reference_price: float | None, observed_price: float | None) -> float | None:
        if reference_price is None or observed_price is None:
            return None
        return abs(float(observed_price) - float(reference_price))

    def _return_report(
        self,
        intent: ExecutionIntent,
        context: PreExecutionContext,
        report: ExecutionReport,
    ) -> ExecutionReport:
        self._write_execution_ledger_record(
            intent=intent,
            context=context,
            report=report,
            adapter_name="demo",
        )
        return report

    def _finalize_without_submission(
        self,
        intent: ExecutionIntent,
        context: PreExecutionContext,
        *,
        exec_state: ExecutionState,
        initial_result: ExecutionInitialResult | None,
        final_result: ExecutionFinalResult | None,
        reason_summary: str,
        request: ExecutionRequest | None = None,
        divergence_flag: bool = False,
        divergence_class: str | None = None,
        slippage_value: float | None = None,
    ) -> ExecutionReport:
        snapshot = ExecutionSnapshot(
            intent_id=intent.intent_id,
            decision_cycle_id=intent.decision_cycle_id,
            request_id=request.request_id if request else None,
            exec_state=exec_state,
            initial_result=initial_result,
            final_result=final_result,
            created_at_utc=context.now_utc,
            updated_at_utc=context.now_utc,
            divergence_flag=divergence_flag,
            divergence_class=divergence_class,
            slippage_value=slippage_value,
            reason_summary=reason_summary,
        )
        return self._finalize(intent, snapshot, request=request)

    def _finalize(
        self,
        intent: ExecutionIntent,
        snapshot: ExecutionSnapshot,
        *,
        request: ExecutionRequest | None = None,
    ) -> ExecutionReport:
        self._snapshots[intent.intent_id] = snapshot
        state_update = snapshot.to_state_update()
        record = IdempotencyRecord(
            intent_id=intent.intent_id,
            decision_cycle_id=intent.decision_cycle_id,
            status=snapshot.exec_state.value,
            first_seen_at_utc=snapshot.created_at_utc,
            last_update_at_utc=snapshot.updated_at_utc,
            submission_ref=request.request_id if request else snapshot.request_id,
            result_state=snapshot.final_result.value if snapshot.final_result else None,
        )
        self._records[intent.intent_id] = record
        return ExecutionReport(
            snapshot=snapshot,
            state_update=state_update,
            core_event_type=state_update.event_type,
            idempotency_record=record,
            request=request,
        )

    def _write_execution_ledger_record(
        self,
        *,
        intent: ExecutionIntent,
        context: PreExecutionContext,
        report: ExecutionReport,
        adapter_name: str,
        transport_result: TransportSubmissionResult | None = None,
        audit_ref: str | None = None,
    ) -> None:
        if self._ledger_store is None:
            return
        self._ledger_store.write_execution_ledger_record(
            ExecutionLedgerRecord(
                intent_id=intent.intent_id,
                decision_cycle_id=intent.decision_cycle_id,
                execution_mode=context.current_mode,
                global_state=context.global_state,
                risk_decision=context.risk_decision,
                market_state=context.market_state,
                market_readiness=context.market_readiness,
                exec_state=report.snapshot.exec_state,
                recorded_at_utc=report.snapshot.updated_at_utc,
                request_id=report.request.request_id if report.request is not None else report.snapshot.request_id,
                initial_result=report.snapshot.initial_result,
                final_result=report.snapshot.final_result,
                reason_summary=report.snapshot.reason_summary,
                slippage_value=report.snapshot.slippage_value,
                adapter_name=adapter_name,
                external_order_ref=(
                    transport_result.external_order_ref if transport_result is not None else None
                ),
                audit_ref=audit_ref,
                was_deduplicated=report.was_deduplicated,
                request_payload=report.request.to_dict() if report.request is not None else {},
                snapshot_payload=report.snapshot.to_dict(),
                idempotency_payload=report.idempotency_record.to_dict(),
                transport_payload=transport_result.to_dict() if transport_result is not None else {},
                context_payload={
                    "kill_active": context.kill_active,
                    "active_block_count": context.active_block_count,
                    "channel_healthy": context.channel_healthy,
                    "current_executable_price": context.current_executable_price,
                    "confirmed_price": context.confirmed_price,
                    "routing_context": dict(context.routing_context),
                },
            )
        )


class ControlledRealExecutionEngine:
    def __init__(
        self,
        adapter: ExecutionTransportAdapter,
        *,
        stricter_max_slippage_factor: float = 0.5,
        ledger_store: ExecutionLedgerWriter | None = None,
    ) -> None:
        self._adapter = adapter
        self._stricter_max_slippage_factor = stricter_max_slippage_factor
        self._records: dict[str, IdempotencyRecord] = {}
        self._snapshots: dict[str, ExecutionSnapshot] = {}
        self._audits: dict[str, RealExecutionAuditRecord] = {}
        self._ledger_store = ledger_store

    def execute(self, intent: ExecutionIntent, context: PreExecutionContext) -> ExecutionReport:
        existing_snapshot = self._snapshots.get(intent.intent_id)
        if existing_snapshot is not None and existing_snapshot.exec_state in FINAL_EXEC_STATES:
            state_update = existing_snapshot.to_state_update()
            record = self._records[intent.intent_id]
            return self._return_report(
                intent,
                context,
                ExecutionReport(
                    snapshot=existing_snapshot,
                    state_update=state_update,
                    core_event_type=state_update.event_type,
                    idempotency_record=record,
                    was_deduplicated=True,
                ),
            )

        rejection_reason = self._precheck_rejection(intent, context)
        if rejection_reason is not None:
            return self._return_report(
                intent,
                context,
                self._finalize_without_submission(
                    intent,
                    context,
                    exec_state=ExecutionState.REJECTED,
                    initial_result=ExecutionInitialResult.REJECTED,
                    final_result=ExecutionFinalResult.CONFIRMED_REJECTED,
                    reason_summary=rejection_reason,
                ),
            )

        if self._is_expired(intent, context.now_utc):
            return self._return_report(
                intent,
                context,
                self._finalize_without_submission(
                    intent,
                    context,
                    exec_state=ExecutionState.CANCELLED_EXPIRED,
                    initial_result=None,
                    final_result=ExecutionFinalResult.CANCELLED_EXPIRED,
                    reason_summary="intent_expired",
                ),
            )

        pre_submission_slippage = self._slippage_value(
            intent.price_reference,
            context.current_executable_price,
        )
        allowed_slippage = float(intent.max_slippage) * self._stricter_max_slippage_factor
        if pre_submission_slippage is not None and pre_submission_slippage > allowed_slippage:
            return self._return_report(
                intent,
                context,
                self._finalize_without_submission(
                    intent,
                    context,
                    exec_state=ExecutionState.REJECTED,
                    initial_result=ExecutionInitialResult.REJECTED,
                    final_result=ExecutionFinalResult.CONFIRMED_REJECTED,
                    reason_summary="real_mode_pre_submission_slippage_guard",
                    slippage_value=pre_submission_slippage,
                ),
            )

        audit_id = make_id("real-audit")
        request = ExecutionRequest(
            request_id=make_id("request"),
            intent_id=intent.intent_id,
            instrument_id=intent.instrument_id,
            side=intent.side,
            target_order_type=intent.target_order_type,
            price_reference=intent.price_reference,
            max_slippage=float(intent.max_slippage),
            created_at_utc=context.now_utc,
            routing_context={
                **context.routing_context,
                "execution_mode": OperationalMode.REAL.value,
                "transport_adapter": self._adapter.adapter_name,
                "audit_ref": audit_id,
            },
        )
        transport_result = self._adapter.submit(request)

        if transport_result.transport_status == TransportSubmissionStatus.REJECTED:
            report = self._finalize_without_submission(
                intent,
                context,
                exec_state=ExecutionState.REJECTED,
                initial_result=ExecutionInitialResult.REJECTED,
                final_result=ExecutionFinalResult.CONFIRMED_REJECTED,
                reason_summary=transport_result.reason_summary or "real_transport_rejected",
                request=request,
            )
        elif transport_result.transport_status == TransportSubmissionStatus.TECHNICAL_FAILURE:
            report = self._finalize_without_submission(
                intent,
                context,
                exec_state=ExecutionState.FAILED,
                initial_result=ExecutionInitialResult.TECHNICAL_FAILURE,
                final_result=ExecutionFinalResult.CONFIRMED_FAILED,
                reason_summary=transport_result.reason_summary or "real_transport_technical_failure",
                request=request,
            )
        elif transport_result.transport_status == TransportSubmissionStatus.AMBIGUOUS:
            report = self._finalize_without_submission(
                intent,
                context,
                exec_state=ExecutionState.DIVERGENT,
                initial_result=ExecutionInitialResult.AMBIGUOUS,
                final_result=ExecutionFinalResult.CRITICAL_DIVERGENCE,
                reason_summary=transport_result.reason_summary or "real_transport_ambiguous",
                request=request,
                divergence_flag=True,
                divergence_class="ambiguous_transport_result",
            )
        else:
            confirmed_price = (
                transport_result.accepted_price
                or context.confirmed_price
                or context.current_executable_price
                or intent.price_reference
            )
            confirmed_slippage = self._slippage_value(intent.price_reference, confirmed_price)
            if confirmed_slippage is not None and confirmed_slippage > float(intent.max_slippage):
                report = self._finalize_without_submission(
                    intent,
                    context,
                    exec_state=ExecutionState.DIVERGENT,
                    initial_result=ExecutionInitialResult.ACCEPTED,
                    final_result=ExecutionFinalResult.CRITICAL_DIVERGENCE,
                    reason_summary="real_mode_slippage_divergence_post_submission",
                    request=request,
                    divergence_flag=True,
                    divergence_class="real_post_submission_slippage",
                    slippage_value=confirmed_slippage,
                )
            else:
                snapshot = ExecutionSnapshot(
                    intent_id=intent.intent_id,
                    decision_cycle_id=intent.decision_cycle_id,
                    request_id=request.request_id,
                    exec_state=ExecutionState.EXECUTION_CONFIRMED,
                    initial_result=ExecutionInitialResult.ACCEPTED,
                    final_result=ExecutionFinalResult.CONFIRMED_EXECUTED,
                    created_at_utc=context.now_utc,
                    updated_at_utc=context.now_utc,
                    divergence_flag=False,
                    slippage_value=confirmed_slippage,
                    reconciliation_confidence=1.0,
                    reason_summary="real_execution_confirmed",
                )
                report = self._finalize(intent, snapshot, request=request)

        self._audits[intent.intent_id] = self._build_audit_record(
            intent=intent,
            request=request,
            report=report,
            transport_result=transport_result,
            context=context,
            audit_id=audit_id,
        )
        return self._return_report(
            intent,
            context,
            report,
            transport_result=transport_result,
            audit_ref=audit_id,
        )

    def export_audit_record(self, path: str | Path, *, intent_id: str | None = None) -> Path:
        record = self._resolve_audit_record(intent_id)
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(record.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return output_path

    def _precheck_rejection(self, intent: ExecutionIntent, context: PreExecutionContext) -> str | None:
        if context.current_mode != OperationalMode.REAL:
            return "mode_incompatible_for_real_exec"
        if context.global_state not in {GlobalState.READY, GlobalState.ACTIVE}:
            return "global_state_incompatible"
        if context.kill_active:
            return "kill_active"
        if context.active_block_count > 0:
            return "active_block_present"
        if context.risk_decision != "ALLOW":
            return "real_mode_requires_risk_allow"
        if context.market_state in {"MS-30", "MS-40", "MS-50"}:
            return "market_incompatible"
        if context.market_readiness in {"NOT_READY", "UNAVAILABLE"}:
            return "market_not_ready"
        if not context.channel_healthy:
            return "execution_channel_unhealthy"
        if not intent.intent_id:
            return "intent_invalid"
        required_fields = ("operator_approval_ref", "approved_by", "change_ticket")
        if any(not context.routing_context.get(field_name) for field_name in required_fields):
            return "real_mode_execution_approval_required"
        return None

    def _is_expired(self, intent: ExecutionIntent, now_utc: datetime) -> bool:
        now_value = ensure_utc(now_utc)
        elapsed_ms = int((now_value - intent.created_at_utc).total_seconds() * 1000)
        return now_value > intent.expires_at_utc or elapsed_ms > intent.ttl_ms

    def _slippage_value(self, reference_price: float | None, observed_price: float | None) -> float | None:
        if reference_price is None or observed_price is None:
            return None
        return abs(float(observed_price) - float(reference_price))

    def _return_report(
        self,
        intent: ExecutionIntent,
        context: PreExecutionContext,
        report: ExecutionReport,
        *,
        transport_result: TransportSubmissionResult | None = None,
        audit_ref: str | None = None,
    ) -> ExecutionReport:
        self._write_execution_ledger_record(
            intent=intent,
            context=context,
            report=report,
            transport_result=transport_result,
            audit_ref=audit_ref,
        )
        return report

    def _finalize_without_submission(
        self,
        intent: ExecutionIntent,
        context: PreExecutionContext,
        *,
        exec_state: ExecutionState,
        initial_result: ExecutionInitialResult | None,
        final_result: ExecutionFinalResult | None,
        reason_summary: str,
        request: ExecutionRequest | None = None,
        divergence_flag: bool = False,
        divergence_class: str | None = None,
        slippage_value: float | None = None,
    ) -> ExecutionReport:
        snapshot = ExecutionSnapshot(
            intent_id=intent.intent_id,
            decision_cycle_id=intent.decision_cycle_id,
            request_id=request.request_id if request else None,
            exec_state=exec_state,
            initial_result=initial_result,
            final_result=final_result,
            created_at_utc=context.now_utc,
            updated_at_utc=context.now_utc,
            divergence_flag=divergence_flag,
            divergence_class=divergence_class,
            slippage_value=slippage_value,
            reason_summary=reason_summary,
        )
        return self._finalize(intent, snapshot, request=request)

    def _finalize(
        self,
        intent: ExecutionIntent,
        snapshot: ExecutionSnapshot,
        *,
        request: ExecutionRequest | None = None,
    ) -> ExecutionReport:
        self._snapshots[intent.intent_id] = snapshot
        state_update = snapshot.to_state_update()
        record = IdempotencyRecord(
            intent_id=intent.intent_id,
            decision_cycle_id=intent.decision_cycle_id,
            status=snapshot.exec_state.value,
            first_seen_at_utc=snapshot.created_at_utc,
            last_update_at_utc=snapshot.updated_at_utc,
            submission_ref=request.request_id if request else snapshot.request_id,
            result_state=snapshot.final_result.value if snapshot.final_result else None,
        )
        self._records[intent.intent_id] = record
        return ExecutionReport(
            snapshot=snapshot,
            state_update=state_update,
            core_event_type=state_update.event_type,
            idempotency_record=record,
            request=request,
        )

    def _write_execution_ledger_record(
        self,
        *,
        intent: ExecutionIntent,
        context: PreExecutionContext,
        report: ExecutionReport,
        transport_result: TransportSubmissionResult | None = None,
        audit_ref: str | None = None,
    ) -> None:
        if self._ledger_store is None:
            return
        self._ledger_store.write_execution_ledger_record(
            ExecutionLedgerRecord(
                intent_id=intent.intent_id,
                decision_cycle_id=intent.decision_cycle_id,
                execution_mode=context.current_mode,
                global_state=context.global_state,
                risk_decision=context.risk_decision,
                market_state=context.market_state,
                market_readiness=context.market_readiness,
                exec_state=report.snapshot.exec_state,
                recorded_at_utc=report.snapshot.updated_at_utc,
                request_id=report.request.request_id if report.request is not None else report.snapshot.request_id,
                initial_result=report.snapshot.initial_result,
                final_result=report.snapshot.final_result,
                reason_summary=report.snapshot.reason_summary,
                slippage_value=report.snapshot.slippage_value,
                adapter_name=self._adapter.adapter_name,
                external_order_ref=(
                    transport_result.external_order_ref if transport_result is not None else None
                ),
                audit_ref=audit_ref,
                was_deduplicated=report.was_deduplicated,
                request_payload=report.request.to_dict() if report.request is not None else {},
                snapshot_payload=report.snapshot.to_dict(),
                idempotency_payload=report.idempotency_record.to_dict(),
                transport_payload=transport_result.to_dict() if transport_result is not None else {},
                context_payload={
                    "kill_active": context.kill_active,
                    "active_block_count": context.active_block_count,
                    "channel_healthy": context.channel_healthy,
                    "current_executable_price": context.current_executable_price,
                    "confirmed_price": context.confirmed_price,
                    "routing_context": dict(context.routing_context),
                },
            )
        )

    def _build_audit_record(
        self,
        *,
        intent: ExecutionIntent,
        request: ExecutionRequest,
        report: ExecutionReport,
        transport_result: TransportSubmissionResult,
        context: PreExecutionContext,
        audit_id: str,
    ) -> RealExecutionAuditRecord:
        return RealExecutionAuditRecord(
            audit_id=audit_id,
            intent_id=intent.intent_id,
            request_id=request.request_id,
            adapter_name=self._adapter.adapter_name,
            operator_approval_ref=str(context.routing_context["operator_approval_ref"]),
            approved_by=str(context.routing_context["approved_by"]),
            change_ticket=str(context.routing_context["change_ticket"]),
            transport_status=transport_result.transport_status.value,
            reason_summary=report.snapshot.reason_summary or "real_execution_audit",
            external_order_ref=transport_result.external_order_ref,
            request_payload=request.to_dict(),
            transport_payload=transport_result.to_dict(),
            snapshot_payload=report.snapshot.to_dict(),
            idempotency_payload=report.idempotency_record.to_dict(),
        )

    def _resolve_audit_record(self, intent_id: str | None) -> RealExecutionAuditRecord:
        if intent_id is not None:
            return self._audits[intent_id]
        if not self._audits:
            raise ValueError("no audit records available")
        return max(self._audits.values(), key=lambda record: record.created_at_utc)

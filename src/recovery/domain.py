from __future__ import annotations

from dataclasses import dataclass

from persistence.state_store import PersistentStateStore
from shared.contracts import (
    ActiveBlockVector,
    ObservedStateSnapshot,
    ReconciliationResult,
    RecoveryConfidenceResult,
    RecoveryContext,
    RecoveryResult,
    RecoverySnapshot,
)
from shared.enums import (
    BlockCode,
    GlobalState,
    RecoveryConfidenceClass,
    RecoveryConsistencyGrade,
    RecoveryIncidentType,
    RecoveryResultCode,
    RecoveryState,
)
from shared.utils import make_id


@dataclass(frozen=True, slots=True)
class RecoveryEvaluation:
    snapshot: RecoverySnapshot
    result: RecoveryResult

    def to_core_event(self):
        return self.result.to_core_event()


class RecoveryOrchestrator:
    def __init__(self, store: PersistentStateStore) -> None:
        self._store = store

    def recover(
        self,
        *,
        incident_type: RecoveryIncidentType,
        observed_state: ObservedStateSnapshot,
        trigger_event_id: str,
        recovery_mode: str = "automatic",
    ) -> RecoveryEvaluation:
        persisted_core = self._store.read_latest_state_snapshot()
        persisted_block_vector = self._store.read_latest_block_vector() or ActiveBlockVector.empty()
        persisted_kill_state = self._store.read_kill_state()
        previous_recovery = self._store.read_latest_recovery_snapshot()

        context = RecoveryContext(
            incident_type=incident_type,
            trigger_event_id=trigger_event_id,
            recovery_mode=recovery_mode,
            persisted_core_snapshot_ref=persisted_core.snapshot_id if persisted_core else None,
            persisted_block_vector_ref=persisted_block_vector.vector_id if persisted_block_vector.blocks else None,
            persisted_kill_flag_ref=persisted_kill_state.kill_id if persisted_kill_state else None,
            persisted_recovery_snapshot_ref=previous_recovery.recovery_snapshot_id if previous_recovery else None,
            current_observed_state_ref=observed_state.observed_snapshot_id,
        )

        reconciliation = self._reconcile(
            context=context,
            observed_state=observed_state,
            persisted_core_state=persisted_core.state_code if persisted_core else None,
            persisted_block_vector=persisted_block_vector,
            persisted_kill_active=bool(persisted_kill_state and persisted_kill_state.is_active),
        )
        confidence = self._evaluate_confidence(
            context=context,
            observed_state=observed_state,
            reconciliation=reconciliation,
            persisted_core_present=persisted_core is not None,
            persisted_kill_active=bool(persisted_kill_state and persisted_kill_state.is_active),
            has_manual_block=persisted_block_vector.has_code(BlockCode.MANUAL),
        )

        snapshot_id = make_id("recovery-snapshot")
        result = self._classify_result(
            context=context,
            observed_state=observed_state,
            persisted_block_vector=persisted_block_vector,
            persisted_kill_active=bool(persisted_kill_state and persisted_kill_state.is_active),
            has_manual_block=persisted_block_vector.has_code(BlockCode.MANUAL),
            confidence=confidence,
            recovery_snapshot_ref=snapshot_id,
        )

        snapshot = RecoverySnapshot(
            recovery_snapshot_id=snapshot_id,
            context=context,
            observed_state=observed_state,
            reconciliation=reconciliation,
            confidence=confidence,
            result=result,
        )
        self._store.write_recovery_snapshot(snapshot)
        return RecoveryEvaluation(snapshot=snapshot, result=result)

    def _reconcile(
        self,
        *,
        context: RecoveryContext,
        observed_state: ObservedStateSnapshot,
        persisted_core_state: GlobalState | None,
        persisted_block_vector: ActiveBlockVector,
        persisted_kill_active: bool,
    ) -> ReconciliationResult:
        conflicts: list[str] = []
        notes: list[str] = []
        grade = RecoveryConsistencyGrade.CONSISTENT

        if persisted_core_state is None:
            conflicts.append("missing_persisted_core_snapshot")
            grade = RecoveryConsistencyGrade.INCONCLUSIVE
        if context.incident_type in {
            RecoveryIncidentType.EXEC_DIVERGENCE,
            RecoveryIncidentType.PERSISTENCE_INCONSISTENT,
        }:
            conflicts.append("incident_requires_manual_review")
            grade = RecoveryConsistencyGrade.DIVERGENT
        if not all(observed_state.module_availability_map.values()):
            conflicts.append("critical_module_unavailable")
            if grade != RecoveryConsistencyGrade.DIVERGENT:
                grade = RecoveryConsistencyGrade.INCONCLUSIVE
        if persisted_kill_active != observed_state.kill_active_observed:
            conflicts.append("kill_state_mismatch")
            if grade != RecoveryConsistencyGrade.DIVERGENT:
                grade = RecoveryConsistencyGrade.INCONCLUSIVE
        if observed_state.market_state in {"MS-20", "MS-30", "MS-40", "MS-50"}:
            notes.append("market_requires_restricted_exit")
            if grade == RecoveryConsistencyGrade.CONSISTENT:
                grade = RecoveryConsistencyGrade.CONSISTENT_WITH_RESTRICTIONS
        if observed_state.risk_state in {"RESTRICT", "RS-20", "RS-50"}:
            notes.append("risk_requires_restricted_exit")
            if grade == RecoveryConsistencyGrade.CONSISTENT:
                grade = RecoveryConsistencyGrade.CONSISTENT_WITH_RESTRICTIONS
        if persisted_block_vector.active_block_count > 0:
            notes.append("active_blocks_persisted")

        return ReconciliationResult(
            recovery_id=context.recovery_id,
            is_consistent=grade in {
                RecoveryConsistencyGrade.CONSISTENT,
                RecoveryConsistencyGrade.CONSISTENT_WITH_RESTRICTIONS,
            },
            consistency_grade=grade,
            conflicts_detected=tuple(conflicts),
            block_vector_consistency="ACTIVE_BLOCKS_PRESENT"
            if persisted_block_vector.active_block_count > 0
            else "NO_PERSISTED_BLOCKS",
            kill_consistency="MATCH" if persisted_kill_active == observed_state.kill_active_observed else "MISMATCH",
            exec_consistency=observed_state.exec_state_summary or "UNKNOWN",
            market_consistency=observed_state.market_state or "UNKNOWN",
            notes=tuple(notes),
        )

    def _evaluate_confidence(
        self,
        *,
        context: RecoveryContext,
        observed_state: ObservedStateSnapshot,
        reconciliation: ReconciliationResult,
        persisted_core_present: bool,
        persisted_kill_active: bool,
        has_manual_block: bool,
    ) -> RecoveryConfidenceResult:
        missing: list[str] = []
        score = 1.0

        if not persisted_core_present:
            missing.append("persisted_core_snapshot")
            score -= 0.35
        if observed_state.market_state is None:
            missing.append("market_state")
            score -= 0.15
        if observed_state.risk_state is None:
            missing.append("risk_state")
            score -= 0.15
        if observed_state.exec_state_summary is None and context.incident_type == RecoveryIncidentType.EXEC_DIVERGENCE:
            missing.append("exec_state_summary")
            score -= 0.25
        if not all(observed_state.module_availability_map.values()):
            score -= 0.25
        if persisted_kill_active or has_manual_block:
            score -= 0.2

        if reconciliation.consistency_grade == RecoveryConsistencyGrade.CONSISTENT:
            confidence_class = RecoveryConfidenceClass.HIGH
        elif reconciliation.consistency_grade == RecoveryConsistencyGrade.CONSISTENT_WITH_RESTRICTIONS:
            confidence_class = RecoveryConfidenceClass.MEDIUM_RESTRICTED
            score = min(score, 0.7)
        elif reconciliation.consistency_grade == RecoveryConsistencyGrade.INCONCLUSIVE:
            confidence_class = RecoveryConfidenceClass.LOW
            score = min(score, 0.4)
        else:
            confidence_class = RecoveryConfidenceClass.UNSAFE
            score = min(score, 0.1)

        score = max(0.0, min(score, 1.0))
        manual_intervention_recommended = confidence_class in {
            RecoveryConfidenceClass.LOW,
            RecoveryConfidenceClass.UNSAFE,
        } or persisted_kill_active or has_manual_block
        safe_to_exit = confidence_class in {
            RecoveryConfidenceClass.HIGH,
            RecoveryConfidenceClass.MEDIUM_RESTRICTED,
        } and not persisted_kill_active and not has_manual_block

        return RecoveryConfidenceResult(
            recovery_id=context.recovery_id,
            confidence_score=score,
            confidence_class=confidence_class,
            missing_critical_evidence=tuple(missing),
            manual_intervention_recommended=manual_intervention_recommended,
            safe_to_exit_recovery=safe_to_exit,
        )

    def _classify_result(
        self,
        *,
        context: RecoveryContext,
        observed_state: ObservedStateSnapshot,
        persisted_block_vector: ActiveBlockVector,
        persisted_kill_active: bool,
        has_manual_block: bool,
        confidence: RecoveryConfidenceResult,
        recovery_snapshot_ref: str,
    ) -> RecoveryResult:
        target_state = None
        result_code = RecoveryResultCode.FAILED
        recovery_state = RecoveryState.FAILED
        summary = "recovery_failed"
        manual_intervention_required = True

        if persisted_kill_active:
            result_code = RecoveryResultCode.MANUAL_REQUIRED
            recovery_state = RecoveryState.MANUAL_REQUIRED
            summary = "recovery_blocked_by_kill_precedence"
        elif has_manual_block:
            result_code = RecoveryResultCode.MANUAL_REQUIRED
            recovery_state = RecoveryState.MANUAL_REQUIRED
            summary = "recovery_blocked_by_manual_precedence"
        elif confidence.confidence_class == RecoveryConfidenceClass.HIGH:
            result_code = RecoveryResultCode.VALIDATED
            recovery_state = RecoveryState.VALIDATED
            target_state = GlobalState.IDLE
            summary = "recovery_validated"
            manual_intervention_required = False
        elif confidence.confidence_class == RecoveryConfidenceClass.MEDIUM_RESTRICTED:
            result_code = RecoveryResultCode.VALIDATED_RESTRICTED
            recovery_state = RecoveryState.VALIDATED_RESTRICTED
            target_state = GlobalState.MONITORING
            summary = "recovery_validated_restricted"
            manual_intervention_required = False
        elif confidence.confidence_class == RecoveryConfidenceClass.LOW:
            result_code = RecoveryResultCode.INCONCLUSIVE
            recovery_state = RecoveryState.INCONCLUSIVE
            summary = "recovery_inconclusive"
        elif confidence.confidence_class == RecoveryConfidenceClass.UNSAFE:
            result_code = RecoveryResultCode.MANUAL_REQUIRED
            recovery_state = RecoveryState.MANUAL_REQUIRED
            summary = "recovery_manual_intervention_required"

        if context.incident_type == RecoveryIncidentType.CRITICAL_MODULE_TIMEOUT and target_state == GlobalState.IDLE:
            target_state = GlobalState.MONITORING
            result_code = RecoveryResultCode.VALIDATED_RESTRICTED
            recovery_state = RecoveryState.VALIDATED_RESTRICTED
            summary = "recovery_validated_after_timeout_restricted"
        if observed_state.market_state in {"MS-20", "MS-30", "MS-40", "MS-50"} and target_state == GlobalState.IDLE:
            target_state = GlobalState.MONITORING
            result_code = RecoveryResultCode.VALIDATED_RESTRICTED
            recovery_state = RecoveryState.VALIDATED_RESTRICTED
            summary = "recovery_validated_with_market_restrictions"

        return RecoveryResult(
            recovery_id=context.recovery_id,
            recovery_state=recovery_state,
            incident_type=context.incident_type,
            result_code=result_code,
            result_summary=summary,
            target_post_recovery_state=target_state,
            manual_intervention_required=manual_intervention_required,
            block_vector_after_recovery=persisted_block_vector.to_dict(),
            reconciliation_confidence=confidence.confidence_score,
            recovery_snapshot_ref=recovery_snapshot_ref,
        )

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from core.blocks import BlockManager
from core.guards import TransitionGuardEngine
from core.heartbeat import HeartbeatSupervisor
from core.publisher import GlobalStatePublisher
from core.startup import StartupOrchestrator
from core.state_machine import CoreStateMachine
from decision import DecisionCycleResult, ExecutionIntent
from exec import DemoExecutionEngine, PreExecutionContext
from learn import LearnStateView, LearningOrchestrator
from market import (
    ContextState,
    FeedIntegrityState,
    MarketAssessment,
    MarketOperationalInput,
    MarketOperationalPipeline,
    MarketReadiness,
    MarketRuntimeStatus,
    MarketState,
)
from persistence.state_store import PersistentStateStore
from persistence.sqlite_state_store import SQLiteStateStore
from risk import RiskDecision, RiskEvaluator, RiskInput
from shared.config import OdinSettings
from shared.contracts import (
    ActiveBlockVector,
    BlockEntry,
    CoreEventEnvelope,
    CorePublicStateView,
    GlobalStateSnapshot,
    PersistentKillState,
)
from shared.enums import (
    BlockCode,
    DecisionOutput,
    DecisionState,
    EventType,
    GlobalState,
    OperationalMode,
    Severity,
)
from shared.utils import utc_now


LOGGER = logging.getLogger(__name__)


class CoreRuntimeController:
    def __init__(
        self,
        settings: OdinSettings,
        *,
        database_path: str | Path | None = None,
        required_modules: list[str] | None = None,
        startup_bootstrap_modules: list[str] | None = None,
        state_store: PersistentStateStore | None = None,
    ) -> None:
        resolved_required_modules = tuple(required_modules or ["MARKET", "RISK", "EXEC"])
        resolved_bootstrap_modules = tuple(startup_bootstrap_modules or resolved_required_modules)
        db_path = Path(database_path) if database_path else settings.runtime.state_dir / "core_state.db"
        self._settings = settings
        self._store = state_store or SQLiteStateStore(db_path)
        self._required_modules = resolved_required_modules
        self._startup_bootstrap_modules = resolved_bootstrap_modules
        self._state_machine = CoreStateMachine()
        self._guard_engine = TransitionGuardEngine()
        self._heartbeat = HeartbeatSupervisor(
            required_modules=list(resolved_required_modules),
            timeout_ms=settings.core.heartbeat_timeout_ms,
            grace_count=settings.core.heartbeat_grace_count,
            startup_timeout_ms=settings.core.startup_timeout_ms,
        )
        self._publisher = GlobalStatePublisher()
        self._startup = StartupOrchestrator(self._store, list(resolved_required_modules))
        self._block_manager = BlockManager()
        self._market_pipeline = MarketOperationalPipeline(settings)
        self._last_market_runtime_status: MarketRuntimeStatus = self._market_pipeline.current_status()
        self._last_market_assessment: MarketAssessment | None = None
        self._risk_evaluator = RiskEvaluator()
        self._demo_exec_engine = DemoExecutionEngine(ledger_store=self._store)
        self._last_risk_assessment: dict[str, Any] | None = None
        self._last_decision_result: dict[str, Any] | None = None
        self._last_execution_summary: dict[str, Any] | None = None
        self._decision_audit_path = self._settings.runtime.log_dir / "decision-cycle-audit.jsonl"
        self._learning = (
            LearningOrchestrator(self._store) if settings.profile.learn_enabled else None
        )
        self._last_persistence_status = "unknown"
        self._last_persistence_error: str | None = None
        self._last_control_action_rejection: str | None = None
        self._current_snapshot = GlobalStateSnapshot.create(
            state_code=GlobalState.OFFLINE,
            mode_code=OperationalMode.DEMO,
            last_transition_event="bootstrap",
            readiness_class=self._state_machine._derive_readiness(
                GlobalState.OFFLINE, ActiveBlockVector.empty(), False
            ),
            integrity_class=self._state_machine._derive_integrity(GlobalState.OFFLINE, False, False),
            kill_active=False,
            active_block_count=0,
            recovery_required=False,
        )

    @property
    def current_snapshot(self) -> GlobalStateSnapshot:
        return self._current_snapshot

    def start(self) -> CorePublicStateView:
        try:
            self._store.initialize()
            persisted_vector = self._store.read_latest_block_vector()
            if persisted_vector is not None:
                self._block_manager = BlockManager(persisted_vector)

            kill_state = self._store.read_kill_state()
            if kill_state is not None and kill_state.is_active and not self._block_manager.as_vector().has_code(
                BlockCode.KILL
            ):
                self._block_manager.apply_block(
                    BlockEntry(
                        block_code=BlockCode.KILL,
                        source_module=kill_state.source_module,
                        severity=Severity.CRITICAL,
                        reason_code=kill_state.reason_code,
                        reason_text=kill_state.reason_text,
                        manual_clear_required=kill_state.manual_clear_required,
                        clearable_by_recovery=False,
                    )
                )

            validation = self._startup.validate()
            self._current_snapshot = GlobalStateSnapshot.create(
                state_code=validation.recommended_entry_state,
                mode_code=OperationalMode.DEMO,
                last_transition_event="startup_validation",
                readiness_class=self._state_machine._derive_readiness(
                    validation.recommended_entry_state,
                    self._block_manager.as_vector(),
                    validation.kill_active,
                ),
                integrity_class=self._state_machine._derive_integrity(
                    validation.recommended_entry_state,
                    validation.kill_active,
                    validation.recommended_entry_state == GlobalState.RECOVERY,
                ),
                kill_active=validation.kill_active,
                active_block_count=self._block_manager.as_vector().active_block_count,
                recovery_required=validation.recommended_entry_state == GlobalState.RECOVERY,
                dominant_block_reason=self._block_manager.as_vector().dominant_block_reason,
            )
            if self._current_snapshot.state_code == GlobalState.STARTUP:
                self._bootstrap_startup_liveness()
                self._promote_startup_when_liveness_ready()
                self._log_startup_liveness_state()
            self._persist_state()
        except Exception as error:
            self._engage_fail_safe(
                reason_code="startup_persistence_failed",
                reason_text="Startup validation could not complete safely due to persistence failure.",
                error=error,
                trigger_event_type="startup",
            )
        return self.get_public_view()

    def process_event(self, event: CoreEventEnvelope) -> CorePublicStateView:
        try:
            rejection_reason = self._validate_control_event(event)
            if rejection_reason is not None:
                self._last_control_action_rejection = rejection_reason
                return self.get_public_view()
            self._last_control_action_rejection = None
            self._apply_side_effect_blocks(event)
            self._current_snapshot = self._state_machine.apply_event(
                event,
                self._current_snapshot,
                self._block_manager.as_vector(),
                self._guard_engine,
            )
            self._persist_state()
        except Exception as error:
            self._engage_fail_safe(
                reason_code="critical_state_persist_failed",
                reason_text=f"Failed to persist critical state while handling {event.event_type}.",
                error=error,
                trigger_event_type=event.event_type,
            )
        return self.get_public_view()

    def record_heartbeat(self, module_name: str) -> None:
        self._heartbeat.record_heartbeat(module_name)

    def evaluate_heartbeats(self) -> list[CorePublicStateView]:
        views: list[CorePublicStateView] = []
        for event in self._heartbeat.evaluate():
            views.append(self.process_event(event))
        if self._current_snapshot.state_code == GlobalState.STARTUP:
            self._promote_startup_when_liveness_ready()
            views.append(self.get_public_view())
        return views

    def shutdown(self) -> CorePublicStateView:
        self._store.mark_clean_shutdown("clean-shutdown", utc_now())
        stop_event = CoreEventEnvelope(
            event_type="EV-STOP",
            source_module="CoreRuntimeController",
            severity=Severity.INFO,
            payload={},
        )
        return self.process_event(stop_event)

    def get_public_view(self) -> CorePublicStateView:
        block_vector = self._block_manager.as_vector()
        liveness_summary = self._heartbeat.liveness_summary()
        return self._publisher.build_view(
            self._current_snapshot,
            block_vector,
            liveness_summary,
            health_metrics=self._build_health_metrics(liveness_summary, block_vector),
            learn_state_view=self._read_learn_state_view(),
        )

    def get_learning_orchestrator(self) -> LearningOrchestrator:
        if self._learning is None:
            raise ValueError("learn disabled for active execution profile")
        return self._learning

    def get_settings(self) -> OdinSettings:
        return self._settings

    def get_state_store(self) -> PersistentStateStore:
        return self._store

    def get_market_runtime_status(self) -> MarketRuntimeStatus:
        return self._last_market_runtime_status

    def get_last_market_assessment(self) -> MarketAssessment | None:
        return self._last_market_assessment

    def get_last_risk_assessment(self) -> dict[str, Any] | None:
        return dict(self._last_risk_assessment) if self._last_risk_assessment is not None else None

    def get_last_decision_result(self) -> dict[str, Any] | None:
        return dict(self._last_decision_result) if self._last_decision_result is not None else None

    def get_last_execution_summary(self) -> dict[str, Any] | None:
        return (
            dict(self._last_execution_summary)
            if self._last_execution_summary is not None
            else None
        )

    def is_feature_enabled(self, feature_name: str) -> bool:
        if feature_name == "learn":
            return self._settings.profile.learn_enabled
        if feature_name == "learn_queries":
            return self._settings.profile.learn_queries_enabled
        if feature_name == "learn_actions":
            return self._settings.profile.learn_actions_enabled
        if feature_name == "shadow_mode":
            return self._settings.profile.shadow_mode_enabled
        if feature_name == "auxiliary_memory":
            return self._settings.profile.auxiliary_memory_enabled
        return False

    def ingest_market_sample(self, sample: MarketOperationalInput) -> CorePublicStateView:
        result = self._market_pipeline.ingest(sample)
        self._last_market_runtime_status = result.runtime_status
        self._last_market_assessment = result.assessment
        self.record_heartbeat("MARKET")
        return self.process_event(result.assessment.to_core_event())

    def run_decision_cycle(
        self,
        *,
        requested_by: str = "console-api",
        mode_override: str | None = None,
        force_risk_block: bool = False,
        force_market_rejected: bool = False,
    ) -> dict[str, Any]:
        decision_mode = (mode_override or self._settings.decision.mode).strip().lower()
        if decision_mode not in {"safe", "test"}:
            decision_mode = "safe"
        now = utc_now()
        public_view = self.get_public_view()
        market_assessment = self._last_market_assessment

        if market_assessment is None:
            return self._finalize_decision_without_intent(
                decision_cycle_id=f"decision-cycle-{now.strftime('%Y%m%d%H%M%S%f')}",
                snapshot_id="decision-snapshot-missing-market",
                operational_output="BLOCKED_BY_MARKET",
                reason_summary="market_sample_missing",
                requested_by=requested_by,
                market_assessment=None,
                risk_assessment=None,
                decision_mode=decision_mode,
                execution_report=None,
            )
        market_readiness = self._build_market_decision_readiness(
            market_assessment=market_assessment,
            now=now,
        )
        if force_market_rejected:
            self.record_heartbeat("DECISION")
            return self._finalize_decision_without_intent(
                decision_cycle_id=f"decision-cycle-{now.strftime('%Y%m%d%H%M%S%f')}",
                snapshot_id=f"decision-snapshot-{now.strftime('%Y%m%d%H%M%S%f')}",
                operational_output="BLOCKED_BY_MARKET",
                reason_summary="market_rejected_forced_for_test",
                requested_by=requested_by,
                market_assessment=market_assessment,
                risk_assessment=None,
                decision_mode=decision_mode,
                execution_report=None,
                market_readiness=market_readiness,
            )

        self.record_heartbeat("RISK")
        risk_input = RiskInput(
            market=market_assessment,
            current_mode=public_view.mode_code,
            kill_switch_active=force_risk_block,
            risk_snapshot_ref=f"risk-{now.strftime('%Y%m%d%H%M%S%f')}",
        )
        risk_assessment = self._risk_evaluator.evaluate(risk_input)
        self.process_event(risk_assessment.to_core_event())
        self._last_risk_assessment = risk_assessment.to_payload()

        decision_cycle_id = f"decision-cycle-{now.strftime('%Y%m%d%H%M%S%f')}"
        snapshot_id = f"decision-snapshot-{now.strftime('%Y%m%d%H%M%S%f')}"
        if not market_readiness["decision_market_ready"]:
            self.record_heartbeat("DECISION")
            return self._finalize_decision_without_intent(
                decision_cycle_id=decision_cycle_id,
                snapshot_id=snapshot_id,
                operational_output="BLOCKED_BY_MARKET",
                reason_summary="market_not_ready_for_decision",
                requested_by=requested_by,
                market_assessment=market_assessment,
                risk_assessment=risk_assessment.to_payload(),
                decision_mode=decision_mode,
                execution_report=None,
                market_readiness=market_readiness,
            )

        if risk_assessment.risk_decision in {RiskDecision.BLOCK, RiskDecision.KILL}:
            self.record_heartbeat("DECISION")
            return self._finalize_decision_without_intent(
                decision_cycle_id=decision_cycle_id,
                snapshot_id=snapshot_id,
                operational_output="BLOCKED_BY_RISK",
                reason_summary=risk_assessment.dominant_risk_reason,
                requested_by=requested_by,
                market_assessment=market_assessment,
                risk_assessment=risk_assessment.to_payload(),
                decision_mode=decision_mode,
                execution_report=None,
                market_readiness=market_readiness,
            )

        if decision_mode == "safe":
            self.record_heartbeat("DECISION")
            return self._finalize_decision_without_intent(
                decision_cycle_id=decision_cycle_id,
                snapshot_id=snapshot_id,
                operational_output="NO_ACTION",
                reason_summary="safe_mode_default_no_action",
                requested_by=requested_by,
                market_assessment=market_assessment,
                risk_assessment=risk_assessment.to_payload(),
                decision_mode=decision_mode,
                execution_report=None,
                market_readiness=market_readiness,
            )

        self.record_heartbeat("DECISION")
        intent = ExecutionIntent.create(
            intent_id=f"intent-{now.strftime('%Y%m%d%H%M%S%f')}",
            decision_cycle_id=decision_cycle_id,
            ttl_ms=self._settings.exec.default_ttl_ms,
            instrument_id=self._last_market_runtime_status.last_instrument_id or "EURUSD",
            side=self._settings.decision.test_side,
            target_order_type="MARKET",
            max_slippage=self._settings.exec.default_max_slippage,
            market_snapshot_ref=snapshot_id,
            risk_snapshot_ref=str(risk_input.risk_snapshot_ref),
            created_at_utc=now,
            hypothesis_id=f"hyp-{now.strftime('%H%M%S')}",
            tactic_id=self._settings.decision.tactic_id,
            price_reference=1.0,
            decision_config_version="decision-lite-v1",
            reason_summary="test_mode_candidate_selected_after_valid_market_sample",
            intent_direction=self._settings.decision.test_side,
            restriction_flags=tuple(),
        )
        decision_result = DecisionCycleResult(
            decision_cycle_id=decision_cycle_id,
            snapshot_id=snapshot_id,
            decision_state=DecisionState.INTENT_EMITTED,
            decision_output=DecisionOutput.CANDIDATE_SELECTED,
            winner_hypothesis_id=intent.hypothesis_id,
            selected_tactic_id=intent.tactic_id,
            intent_id=intent.intent_id,
            intent_emitted=True,
            blocked_by_external=False,
            reason_summary=intent.reason_summary or "candidate_selected",
            generated_at_utc=now,
        )
        self.process_event(decision_result.to_core_event())
        self._last_decision_result = {
            **decision_result.to_dict(),
            "operational_output": "CANDIDATE_SELECTED",
            "score": self._settings.decision.test_score,
            "decision_mode": decision_mode,
            "tactic_id": intent.tactic_id,
        }

        execution_context = PreExecutionContext(
            global_state=self.get_public_view().state_code,
            current_mode=self.get_public_view().mode_code,
            risk_decision=risk_assessment.risk_decision.value,
            market_state=market_assessment.market_state.value,
            market_readiness=market_assessment.readiness_state.value,
            current_executable_price=1.0,
            confirmed_price=1.0,
        )
        self.record_heartbeat("EXEC")
        execution_report = self._demo_exec_engine.execute(intent, execution_context)
        self.process_event(execution_report.to_core_event())
        ledger_ref = self._latest_execution_ledger_ref_for_intent(intent.intent_id)
        self._last_execution_summary = {
            "core_event_type": execution_report.core_event_type,
            "snapshot": execution_report.snapshot.to_dict(),
            "request": execution_report.request.to_dict() if execution_report.request else None,
            "was_deduplicated": execution_report.was_deduplicated,
            "execution_ledger_ref": ledger_ref,
        }
        decision_summary = self._build_decision_summary(
            decision=self._last_decision_result,
            execution_ledger_ref=ledger_ref,
        )
        response = {
            "accepted": True,
            "decision_mode": decision_mode,
            "decision": dict(self._last_decision_result),
            "decision_summary": decision_summary,
            **decision_summary,
            "intent": intent.to_dict(),
            "risk": risk_assessment.to_payload(),
            "market": market_assessment.to_payload(),
            "market_debug": market_readiness,
            "execution": dict(self._last_execution_summary),
        }
        self._append_decision_audit_record(
            requested_by=requested_by,
            payload=response,
        )
        return response

    def validate_mode_change_request(
        self,
        target_mode: OperationalMode,
        *,
        authorization_context: dict[str, Any] | None = None,
        reason_text: str | None = None,
    ) -> tuple[bool, str | None]:
        payload = dict(authorization_context or {})
        if reason_text:
            payload["reason_text"] = reason_text
        payload["mode_code"] = target_mode.value
        rejection_reason = self._validate_mode_change_payload(target_mode, payload)
        return rejection_reason is None, rejection_reason

    def _apply_side_effect_blocks(self, event: CoreEventEnvelope) -> None:
        if event.event_type == "EV-KILL-ACTIVE":
            kill_reason = event.payload.get("reason_code") or event.payload.get(
                "dominant_risk_reason", "kill_active"
            )
            kill_state = PersistentKillState(
                is_active=True,
                source_module=event.source_module,
                reason_code=str(kill_reason),
                reason_text=event.payload.get("reason_text"),
            )
            self._store.write_kill_state(kill_state)
            self._block_manager.apply_block(
                BlockEntry(
                    block_code=BlockCode.KILL,
                    source_module=event.source_module,
                    severity=Severity.CRITICAL,
                    reason_code=kill_state.reason_code,
                    reason_text=kill_state.reason_text,
                    manual_clear_required=True,
                    clearable_by_recovery=False,
                )
            )
        elif event.event_type == "EV-RISK-BLOCK":
            risk_reason = event.payload.get("reason_code") or event.payload.get(
                "dominant_risk_reason", "risk_block"
            )
            self._block_manager.apply_block(
                BlockEntry(
                    block_code=BlockCode.RISK,
                    source_module=event.source_module,
                    severity=Severity.ERROR,
                    reason_code=str(risk_reason),
                    reason_text=event.payload.get("reason_text"),
                    manual_clear_required=False,
                    clearable_by_recovery=True,
                )
            )
        elif event.event_type in {"EV-RISK-ALLOW", "EV-RISK-RESTRICT"}:
            self._block_manager.clear_by_code(BlockCode.RISK)
        elif event.event_type == EventType.MANUAL_BLOCK.value:
            self._block_manager.apply_block(
                BlockEntry(
                    block_code=BlockCode.MANUAL,
                    source_module=event.source_module,
                    severity=Severity.ERROR,
                    reason_code=str(event.payload.get("reason_code", "manual_block_active")),
                    reason_text=event.payload.get("reason_text"),
                    manual_clear_required=True,
                    clearable_by_recovery=False,
                )
            )
        elif event.event_type == EventType.MANUAL_CLEAR.value:
            self._block_manager.clear_by_code(BlockCode.MANUAL, allow_manual=True)
        elif event.event_type in {
            "EV-FAULT-BLOCK",
            "EV-HB-TIMEOUT",
            "EV-EXEC-DIVERGENCE",
            "EV-PERSISTENCE-INCONSISTENT",
            "EV-MODULE-UNAVAILABLE",
        }:
            fault_reason = (
                event.payload.get("reason_code")
                or event.payload.get("reason_summary")
                or "fault_block"
            )
            self._block_manager.apply_block(
                BlockEntry(
                    block_code=BlockCode.FAULT,
                    source_module=event.source_module,
                    severity=Severity.CRITICAL,
                    reason_code=str(fault_reason),
                    reason_text=event.payload.get("reason_text"),
                    manual_clear_required=False,
                    clearable_by_recovery=True,
                )
            )
        elif event.event_type == "EV-RECOVERY-START":
            self._block_manager.apply_block(
                BlockEntry(
                    block_code=BlockCode.RECOVERY_PENDING,
                    source_module=event.source_module,
                    severity=Severity.ERROR,
                    reason_code="recovery_pending",
                    manual_clear_required=False,
                    clearable_by_recovery=True,
                )
            )
        elif event.event_type in {"EV-RECOVERY-OK", "EV-RECOVERY-OK-RESTRICTED"}:
            self._block_manager.clear_by_code(BlockCode.RECOVERY_PENDING, via_recovery=True)
            self._block_manager.clear_by_code(BlockCode.FAULT, via_recovery=True)
        elif event.event_type in {"EV-RECOVERY-FAIL", "EV-RECOVERY-INTERVENTION-REQUIRED"}:
            self._block_manager.apply_block(
                BlockEntry(
                    block_code=BlockCode.FAULT,
                    source_module=event.source_module,
                    severity=Severity.CRITICAL,
                    reason_code=str(event.payload.get("result_summary", "recovery_failed")),
                    reason_text=event.payload.get("reason_text"),
                    manual_clear_required=False,
                    clearable_by_recovery=True,
                )
            )
        elif event.event_type == "EV-KILL-CLEARED":
            self._block_manager.clear_by_code(BlockCode.KILL, allow_manual=True)
            self._store.write_kill_state(
                PersistentKillState(
                    is_active=False,
                    source_module=event.source_module,
                    reason_code="kill_cleared",
                    activated_by=event.source_module,
                    manual_clear_required=False,
                )
            )

    def _persist_state(self) -> None:
        self._store.write_block_vector(self._block_manager.as_vector())
        if self._settings.core.persist_on_critical_transition:
            self._store.write_state_snapshot(self._current_snapshot)
        self._mark_persistence_healthy()

    def _build_health_metrics(
        self,
        liveness_summary: dict[str, str],
        block_vector: ActiveBlockVector,
    ) -> dict[str, object]:
        startup_missing_modules = sorted(
            module_name
            for module_name, status in liveness_summary.items()
            if status == "NOT_STARTED"
        )
        startup_unavailable_modules = sorted(
            module_name
            for module_name, status in liveness_summary.items()
            if status == "UNAVAILABLE"
        )
        return {
            "persistence_status": self._last_persistence_status,
            "last_persistence_error": self._last_persistence_error,
            "fail_safe_engaged": self._current_snapshot.state_code == GlobalState.BLOCKED_FAULT
            and block_vector.has_code(BlockCode.FAULT),
            "critical_module_timeout_count": sum(status == "TIMEOUT" for status in liveness_summary.values()),
            "critical_module_delayed_count": sum(status == "DELAYED" for status in liveness_summary.values()),
            "critical_module_ok_count": sum(status == "OK" for status in liveness_summary.values()),
            "last_control_action_rejection": self._last_control_action_rejection,
            "active_block_vector": block_vector.to_dict(),
            "active_block_codes": [block.block_code.value for block in block_vector.blocks],
            "startup_required_modules": list(self._required_modules),
            "startup_missing_heartbeat_modules": startup_missing_modules,
            "startup_unavailable_modules": startup_unavailable_modules,
        }

    def _mark_persistence_healthy(self) -> None:
        self._last_persistence_status = "ok"
        self._last_persistence_error = None

    def _read_learn_state_view(self) -> LearnStateView | None:
        if self._learning is None:
            return None
        try:
            return self._learning.read_state_view()
        except Exception:
            return None

    def _engage_fail_safe(
        self,
        *,
        reason_code: str,
        reason_text: str,
        error: Exception,
        trigger_event_type: str,
    ) -> None:
        self._last_persistence_status = "failed"
        self._last_persistence_error = f"{error.__class__.__name__}: {error}"
        self._block_manager.apply_block(
            BlockEntry(
                block_code=BlockCode.FAULT,
                source_module="CORE",
                severity=Severity.CRITICAL,
                reason_code=reason_code,
                reason_text=reason_text,
                manual_clear_required=False,
                clearable_by_recovery=True,
                metadata={
                    "error_type": error.__class__.__name__,
                    "trigger_event_type": trigger_event_type,
                },
            )
        )
        block_vector = self._block_manager.as_vector()
        kill_active = block_vector.has_code(BlockCode.KILL)
        self._current_snapshot = GlobalStateSnapshot.create(
            state_code=GlobalState.BLOCKED_FAULT,
            mode_code=self._current_snapshot.mode_code,
            last_transition_event=EventType.PERSISTENCE_INCONSISTENT.value,
            readiness_class=self._state_machine._derive_readiness(
                GlobalState.BLOCKED_FAULT,
                block_vector,
                kill_active,
            ),
            integrity_class=self._state_machine._derive_integrity(
                GlobalState.BLOCKED_FAULT,
                kill_active,
                False,
            ),
            kill_active=kill_active,
            active_block_count=block_vector.active_block_count,
            recovery_required=False,
            dominant_block_reason=block_vector.dominant_block_reason,
        )

    def _finalize_decision_without_intent(
        self,
        *,
        decision_cycle_id: str,
        snapshot_id: str,
        operational_output: str,
        reason_summary: str,
        requested_by: str,
        market_assessment: MarketAssessment | None,
        risk_assessment: dict[str, Any] | None,
        decision_mode: str,
        execution_report: dict[str, Any] | None,
        market_readiness: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        decision_result = DecisionCycleResult(
            decision_cycle_id=decision_cycle_id,
            snapshot_id=snapshot_id,
            decision_state=(
                DecisionState.BLOCKED_EXTERNALLY
                if operational_output in {"BLOCKED_BY_MARKET", "BLOCKED_BY_RISK"}
                else DecisionState.NO_VALID_OPPORTUNITY
            ),
            decision_output=(
                DecisionOutput.BLOCKED
                if operational_output in {"BLOCKED_BY_MARKET", "BLOCKED_BY_RISK"}
                else DecisionOutput.NO_ACTION
            ),
            winner_hypothesis_id=None,
            selected_tactic_id=self._settings.decision.tactic_id,
            intent_id=None,
            intent_emitted=False,
            blocked_by_external=operational_output in {"BLOCKED_BY_MARKET", "BLOCKED_BY_RISK"},
            reason_summary=reason_summary,
            generated_at_utc=now,
        )
        self.process_event(decision_result.to_core_event())
        self._last_decision_result = {
            **decision_result.to_dict(),
            "operational_output": operational_output,
            "score": None,
            "decision_mode": decision_mode,
            "tactic_id": self._settings.decision.tactic_id,
        }
        self._last_execution_summary = execution_report
        decision_summary = self._build_decision_summary(
            decision=self._last_decision_result,
            execution_ledger_ref=None,
        )
        response = {
            "accepted": False,
            "decision_mode": decision_mode,
            "decision": dict(self._last_decision_result),
            "decision_summary": decision_summary,
            **decision_summary,
            "intent": None,
            "risk": risk_assessment,
            "market": market_assessment.to_payload() if market_assessment is not None else None,
            "market_debug": dict(market_readiness or {}),
            "execution": execution_report,
        }
        self._append_decision_audit_record(
            requested_by=requested_by,
            payload=response,
        )
        return response

    def _append_decision_audit_record(
        self,
        *,
        requested_by: str,
        payload: dict[str, Any],
    ) -> None:
        record = {
            "ts_utc": utc_now().isoformat(),
            "requested_by": requested_by,
            "event": "decision_cycle_run",
            **payload,
        }
        self._decision_audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self._decision_audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _latest_execution_ledger_ref_for_intent(self, intent_id: str) -> str | None:
        records = self._store.list_execution_ledger_records(intent_id=intent_id)
        if not records:
            return None
        return records[-1].ledger_id

    def _build_decision_summary(
        self,
        *,
        decision: dict[str, Any] | None,
        execution_ledger_ref: str | None,
    ) -> dict[str, Any]:
        payload = dict(decision or {})
        return {
            "decision_cycle_id": payload.get("decision_cycle_id"),
            "operational_output": payload.get("operational_output"),
            "reason_summary": payload.get("reason_summary"),
            "tactic_id": payload.get("tactic_id"),
            "score": payload.get("score"),
            "intent_id": payload.get("intent_id"),
            "execution_ledger_ref": execution_ledger_ref,
        }

    def _build_market_decision_readiness(
        self,
        *,
        market_assessment: MarketAssessment,
        now: datetime,
    ) -> dict[str, Any]:
        max_valid_age_ms = int(self._settings.market.max_valid_age_ms)
        max_degraded_age_ms = int(self._settings.market.max_degraded_age_ms)
        sample_age_ms = max(
            0,
            int((now - market_assessment.last_valid_update_utc).total_seconds() * 1000),
        )
        reason_code = "market_ready_for_decision"
        decision_market_ready = True
        if self._last_market_runtime_status.last_gate_status != "accepted":
            reason_code = "market_profile_rejected"
            decision_market_ready = False
        elif sample_age_ms > max_degraded_age_ms:
            reason_code = "feed_too_stale"
            decision_market_ready = False
        elif market_assessment.market_state in {
            MarketState.INVALID,
            MarketState.CLOSED,
            MarketState.UNAVAILABLE,
        }:
            reason_code = "market_state_not_ready"
            decision_market_ready = False
        elif market_assessment.readiness_state in {
            MarketReadiness.NOT_READY,
            MarketReadiness.UNAVAILABLE,
        }:
            reason_code = "market_readiness_not_ready"
            decision_market_ready = False
        elif market_assessment.feed_integrity_state in {
            FeedIntegrityState.INVALID,
            FeedIntegrityState.UNAVAILABLE,
        }:
            reason_code = "feed_integrity_not_ready"
            decision_market_ready = False
        elif market_assessment.context_state == ContextState.HOSTILE:
            reason_code = "market_context_hostile"
            decision_market_ready = False

        return {
            "decision_market_ready": decision_market_ready,
            "reason_code": reason_code,
            "sample_age_ms": sample_age_ms,
            "max_valid_age_ms": max_valid_age_ms,
            "max_degraded_age_ms": max_degraded_age_ms,
            "market_assessment_state": market_assessment.market_state.value,
            "market_readiness_state": market_assessment.readiness_state.value,
            "feed_integrity_state": market_assessment.feed_integrity_state.value,
            "last_valid_update_utc": market_assessment.last_valid_update_utc.isoformat(),
            "evaluated_at_utc": now.isoformat(),
        }

    def _validate_control_event(self, event: CoreEventEnvelope) -> str | None:
        if event.event_type != EventType.MODE_CHANGE.value:
            return None
        mode_code = event.payload.get("mode_code")
        if mode_code is None:
            return "target_mode_required"
        return self._validate_mode_change_payload(
            OperationalMode(mode_code),
            event.payload,
        )

    def _validate_mode_change_payload(
        self,
        target_mode: OperationalMode,
        payload: dict[str, Any],
    ) -> str | None:
        block_vector = self._block_manager.as_vector()
        if target_mode == OperationalMode.REAL:
            if not self._settings.core.allow_real_mode:
                return "real_mode_disabled"
            if self._current_snapshot.state_code not in {
                GlobalState.IDLE,
                GlobalState.MONITORING,
                GlobalState.READY,
            }:
                return "state_incompatible_for_real_mode"
            if self._current_snapshot.kill_active or block_vector.active_block_count > 0:
                return "active_block_or_kill_present"
            if (
                self._settings.real.require_explicit_confirmation
                and payload.get("real_mode_confirmation") != self._settings.real.confirmation_phrase
            ):
                return "real_mode_confirmation_required"
            if self._settings.real.require_change_ticket and not payload.get("change_ticket"):
                return "change_ticket_required"
            if self._settings.real.require_approval_ref and (
                not payload.get("approval_ref") or not payload.get("approved_by")
            ):
                return "approval_ref_required"
            if self._settings.real.require_all_heartbeats_ok:
                liveness_summary = self._heartbeat.liveness_summary()
                if any(liveness_summary.get(module_name) != "OK" for module_name in self._required_modules):
                    return "critical_module_liveness_not_ok"
        elif self._current_snapshot.mode_code == OperationalMode.REAL and (
            payload.get("rollback_reason") is None and payload.get("reason_text") is None
        ):
            return "rollback_reason_required"
        return None

    def _bootstrap_startup_liveness(self) -> None:
        for module_name in self._startup_bootstrap_modules:
            if module_name not in self._required_modules:
                continue
            startup_event = self._heartbeat.emit_startup_heartbeat(module_name)
            LOGGER.info(
                "startup_heartbeat_received module=%s event_type=%s reason=%s",
                module_name,
                startup_event.event_type,
                startup_event.payload.get("reason_code"),
            )

    def _modules_ready_for_startup_exit(self) -> bool:
        liveness = self._heartbeat.liveness_summary()
        return all(liveness.get(module_name) == "OK" for module_name in self._required_modules)

    def _promote_startup_when_liveness_ready(self) -> None:
        if self._current_snapshot.state_code != GlobalState.STARTUP:
            return
        block_vector = self._block_manager.as_vector()
        if block_vector.has_code(BlockCode.KILL) or block_vector.active_block_count > 0:
            return
        if not self._modules_ready_for_startup_exit():
            return

        self._current_snapshot = GlobalStateSnapshot.create(
            state_code=GlobalState.MONITORING,
            mode_code=self._current_snapshot.mode_code,
            last_transition_event=EventType.HB_OK.value,
            readiness_class=self._state_machine._derive_readiness(
                GlobalState.MONITORING,
                block_vector,
                False,
            ),
            integrity_class=self._state_machine._derive_integrity(
                GlobalState.MONITORING,
                False,
                False,
            ),
            kill_active=False,
            active_block_count=block_vector.active_block_count,
            recovery_required=False,
            dominant_block_reason=block_vector.dominant_block_reason,
        )

    def _log_startup_liveness_state(self) -> None:
        liveness = self._heartbeat.liveness_summary()
        detected_modules = sorted(
            module_name for module_name, status in liveness.items() if status == "OK"
        )
        missing_modules = sorted(
            module_name for module_name, status in liveness.items() if status == "NOT_STARTED"
        )
        unavailable_modules = sorted(
            module_name for module_name, status in liveness.items() if status == "UNAVAILABLE"
        )
        LOGGER.info(
            "startup_liveness detected=%s missing=%s unavailable=%s state=%s",
            detected_modules,
            missing_modules,
            unavailable_modules,
            self._current_snapshot.state_code.value,
        )
        if self._current_snapshot.state_code == GlobalState.STARTUP:
            LOGGER.warning(
                "startup_stalled state=ST-10 reason=required_modules_without_heartbeat missing=%s unavailable=%s",
                missing_modules,
                unavailable_modules,
            )

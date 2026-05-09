from __future__ import annotations

from shared.contracts import ActiveBlockVector, CoreEventEnvelope, GlobalStateSnapshot
from shared.enums import BlockCode, EventType, GlobalState, IntegrityClass, OperationalMode, ReadinessClass
from core.guards import TransitionGuardEngine


class CoreStateMachine:
    def determine_target_state(
        self,
        current_state: GlobalState,
        event_type: str,
    ) -> GlobalState:
        event = EventType(event_type)
        if event == EventType.START:
            return GlobalState.STARTUP if current_state == GlobalState.OFFLINE else current_state
        if event == EventType.STOP:
            return GlobalState.OFFLINE
        if event == EventType.PAUSE and current_state in {
            GlobalState.MONITORING,
            GlobalState.READY,
            GlobalState.ACTIVE,
        }:
            return GlobalState.PAUSED
        if event == EventType.MANUAL_BLOCK and current_state in {
            GlobalState.IDLE,
            GlobalState.MONITORING,
            GlobalState.READY,
            GlobalState.ACTIVE,
            GlobalState.PAUSED,
        }:
            return GlobalState.PAUSED
        if event == EventType.RESUME and current_state in {
            GlobalState.PAUSED,
            GlobalState.BLOCKED_RISK,
        }:
            return GlobalState.MONITORING
        if event == EventType.MANUAL_CLEAR and current_state == GlobalState.PAUSED:
            return GlobalState.MONITORING
        if event == EventType.MAINTENANCE_ENTER:
            return GlobalState.MAINTENANCE
        if event == EventType.MAINTENANCE_EXIT and current_state == GlobalState.MAINTENANCE:
            return GlobalState.IDLE
        if event == EventType.MARKET_READY and current_state == GlobalState.STARTUP:
            return GlobalState.MONITORING
        if event in {
            EventType.MARKET_DEGRADED,
            EventType.MARKET_INVALID,
            EventType.MARKET_CLOSED,
            EventType.MARKET_HOSTILE,
            EventType.MARKET_NEWS_GUARD,
        } and current_state == GlobalState.STARTUP:
            return GlobalState.MONITORING
        if event == EventType.MARKET_READY and current_state in {
            GlobalState.IDLE,
            GlobalState.MONITORING,
            GlobalState.PAUSED,
        }:
            return GlobalState.READY
        if event in {
            EventType.MARKET_DEGRADED,
            EventType.MARKET_INVALID,
            EventType.MARKET_CLOSED,
            EventType.MARKET_HOSTILE,
            EventType.MARKET_NEWS_GUARD,
        } and current_state in {GlobalState.READY, GlobalState.ACTIVE, GlobalState.PAUSED}:
            return GlobalState.MONITORING
        if event == EventType.RISK_BLOCK:
            return GlobalState.BLOCKED_RISK
        if event in {
            EventType.KILL_ACTIVE,
            EventType.FAULT_BLOCK,
            EventType.HB_TIMEOUT,
            EventType.EXEC_DIVERGENCE,
            EventType.PERSISTENCE_INCONSISTENT,
            EventType.MODULE_UNAVAILABLE,
        }:
            return GlobalState.BLOCKED_FAULT
        if event == EventType.EXEC_CONFIRMED and current_state == GlobalState.READY:
            return GlobalState.ACTIVE
        if event in {
            EventType.EXEC_REJECTED,
            EventType.EXEC_REJECTED_SLIPPAGE,
            EventType.INTENTION_EXPIRED,
        } and current_state == GlobalState.ACTIVE:
            return GlobalState.MONITORING
        if event == EventType.RECOVERY_START:
            return GlobalState.RECOVERY
        if event == EventType.RECOVERY_OK:
            return GlobalState.IDLE if current_state == GlobalState.RECOVERY else current_state
        if event == EventType.RECOVERY_OK_RESTRICTED:
            return GlobalState.MONITORING if current_state == GlobalState.RECOVERY else current_state
        if event in {EventType.RECOVERY_FAIL, EventType.RECOVERY_INTERVENTION_REQUIRED, EventType.ERROR}:
            return GlobalState.ERROR
        return current_state

    def apply_event(
        self,
        event: CoreEventEnvelope,
        current_snapshot: GlobalStateSnapshot,
        block_vector: ActiveBlockVector,
        guard_engine: TransitionGuardEngine,
    ) -> GlobalStateSnapshot:
        target_state = self.determine_target_state(current_snapshot.state_code, event.event_type)
        if target_state != current_snapshot.state_code:
            guard = guard_engine.evaluate(event, current_snapshot, target_state, block_vector)
            if not guard.allowed:
                return self._snapshot_from_state(
                    state_code=current_snapshot.state_code,
                    current_snapshot=current_snapshot,
                    block_vector=block_vector,
                    transition_event=event.event_type,
                )

        new_mode = current_snapshot.mode_code
        if event.event_type == EventType.MODE_CHANGE.value and "mode_code" in event.payload:
            new_mode = OperationalMode(event.payload["mode_code"])

        return self._snapshot_from_state(
            state_code=target_state,
            current_snapshot=current_snapshot,
            block_vector=block_vector,
            transition_event=event.event_type,
            mode_code=new_mode,
        )

    def _snapshot_from_state(
        self,
        *,
        state_code: GlobalState,
        current_snapshot: GlobalStateSnapshot,
        block_vector: ActiveBlockVector,
        transition_event: str,
        mode_code: OperationalMode | None = None,
    ) -> GlobalStateSnapshot:
        kill_active = block_vector.has_code(BlockCode.KILL)
        recovery_required = state_code == GlobalState.RECOVERY
        readiness_class = self._derive_readiness(state_code, block_vector, kill_active)
        integrity_class = self._derive_integrity(state_code, kill_active, recovery_required)
        return GlobalStateSnapshot.create(
            state_code=state_code,
            mode_code=mode_code or current_snapshot.mode_code,
            last_transition_event=transition_event,
            readiness_class=readiness_class,
            integrity_class=integrity_class,
            kill_active=kill_active,
            active_block_count=block_vector.active_block_count,
            recovery_required=recovery_required,
            dominant_block_reason=block_vector.dominant_block_reason,
        )

    def _derive_readiness(
        self,
        state_code: GlobalState,
        block_vector: ActiveBlockVector,
        kill_active: bool,
    ) -> ReadinessClass:
        if kill_active or block_vector.active_block_count > 0:
            return ReadinessClass.BLOCKED
        if state_code == GlobalState.STARTUP:
            return ReadinessClass.STARTING
        if state_code == GlobalState.MONITORING:
            return ReadinessClass.MONITORING
        if state_code == GlobalState.READY:
            return ReadinessClass.READY
        if state_code == GlobalState.ACTIVE:
            return ReadinessClass.ACTIVE
        if state_code == GlobalState.PAUSED:
            return ReadinessClass.PAUSED
        if state_code == GlobalState.MAINTENANCE:
            return ReadinessClass.MAINTENANCE
        if state_code == GlobalState.TRAINING:
            return ReadinessClass.TRAINING
        if state_code == GlobalState.RECOVERY:
            return ReadinessClass.RECOVERY
        return ReadinessClass.MONITORING

    def _derive_integrity(
        self,
        state_code: GlobalState,
        kill_active: bool,
        recovery_required: bool,
    ) -> IntegrityClass:
        if kill_active or state_code in {GlobalState.BLOCKED_FAULT, GlobalState.ERROR}:
            return IntegrityClass.BLOCKED
        if recovery_required:
            return IntegrityClass.RECOVERY_REQUIRED
        if state_code in {GlobalState.STARTUP, GlobalState.MONITORING, GlobalState.BLOCKED_RISK}:
            return IntegrityClass.DEGRADED
        return IntegrityClass.OK

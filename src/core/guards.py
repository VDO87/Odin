from __future__ import annotations

from shared.contracts import ActiveBlockVector, CoreEventEnvelope, GlobalStateSnapshot, TransitionGuardResult
from shared.enums import BlockCode, GlobalState


class TransitionGuardEngine:
    _BLOCK_PRECEDENCE: tuple[BlockCode, ...] = (
        BlockCode.KILL,
        BlockCode.MANUAL,
        BlockCode.FAULT,
        BlockCode.RECOVERY_PENDING,
        BlockCode.RISK,
        BlockCode.ADMIN,
        BlockCode.MAINTENANCE,
    )
    _BLOCK_RULES: dict[BlockCode, tuple[str, str]] = {
        BlockCode.KILL: ("kill_active", "clear_kill_manually"),
        BlockCode.MANUAL: ("manual_block_active", "clear_manual_block"),
        BlockCode.FAULT: ("fault_block_active", "execute_recovery"),
        BlockCode.RECOVERY_PENDING: ("recovery_pending", "complete_recovery"),
        BlockCode.RISK: ("risk_block_active", "wait_for_risk_clear"),
        BlockCode.ADMIN: ("administrative_block_active", "clear_administrative_block"),
        BlockCode.MAINTENANCE: ("maintenance_block_active", "exit_maintenance_cleanly"),
    }

    def evaluate(
        self,
        event: CoreEventEnvelope,
        current_snapshot: GlobalStateSnapshot,
        requested_to_state: GlobalState,
        block_vector: ActiveBlockVector,
    ) -> TransitionGuardResult:
        blocked_reason: str | None = None
        operator_action: str | None = None

        if requested_to_state == GlobalState.ACTIVE:
            blocking_code = self._highest_precedence_active_block(block_vector)
            if current_snapshot.kill_active or blocking_code == BlockCode.KILL:
                blocked_reason = "kill_active"
                operator_action = "clear_kill_manually"
            elif blocking_code is not None:
                blocked_reason, operator_action = self._BLOCK_RULES[blocking_code]
            elif current_snapshot.recovery_required:
                blocked_reason = "recovery_required"
                operator_action = "complete_recovery"
            elif current_snapshot.state_code in {
                GlobalState.OFFLINE,
                GlobalState.STARTUP,
                GlobalState.RECOVERY,
                GlobalState.BLOCKED_RISK,
                GlobalState.BLOCKED_FAULT,
                GlobalState.ERROR,
            }:
                blocked_reason = "forbidden_state_transition"
                operator_action = "return_to_ready_or_idle"

        if requested_to_state == GlobalState.READY:
            blocking_code = self._highest_precedence_active_block(block_vector)
            if current_snapshot.kill_active or blocking_code == BlockCode.KILL:
                blocked_reason = blocked_reason or "kill_active"
                operator_action = operator_action or "clear_kill_manually"
            elif blocking_code is not None:
                reason, action = self._BLOCK_RULES[blocking_code]
                blocked_reason = blocked_reason or reason
                operator_action = operator_action or action

        if requested_to_state in {GlobalState.IDLE, GlobalState.MONITORING}:
            if block_vector.has_code(BlockCode.KILL):
                blocked_reason = blocked_reason or "kill_active"
                operator_action = operator_action or "clear_kill_manually"
            elif (
                current_snapshot.state_code
                in {
                    GlobalState.PAUSED,
                    GlobalState.RECOVERY,
                    GlobalState.BLOCKED_RISK,
                    GlobalState.BLOCKED_FAULT,
                    GlobalState.MAINTENANCE,
                }
                and block_vector.has_code(BlockCode.MANUAL)
            ):
                blocked_reason = blocked_reason or "manual_block_active"
                operator_action = operator_action or "clear_manual_block"
            elif current_snapshot.state_code == GlobalState.RECOVERY and block_vector.has_code(
                BlockCode.RECOVERY_PENDING
            ):
                blocked_reason = blocked_reason or "recovery_pending"
                operator_action = operator_action or "complete_recovery"
            elif current_snapshot.state_code == GlobalState.BLOCKED_FAULT and block_vector.has_code(
                BlockCode.FAULT
            ):
                blocked_reason = blocked_reason or "fault_block_active"
                operator_action = operator_action or "execute_recovery"
            elif (
                current_snapshot.state_code == GlobalState.BLOCKED_RISK
                and block_vector.has_code(BlockCode.RISK)
            ):
                blocked_reason = blocked_reason or "risk_block_active"
                operator_action = operator_action or "wait_for_risk_clear"

        return TransitionGuardResult(
            event_id=event.event_id,
            from_state=current_snapshot.state_code,
            requested_to_state=requested_to_state,
            allowed=blocked_reason is None,
            blocking_reason_code=blocked_reason,
            required_operator_action=operator_action,
        )

    def _highest_precedence_active_block(self, block_vector: ActiveBlockVector) -> BlockCode | None:
        for block_code in self._BLOCK_PRECEDENCE:
            if block_vector.has_code(block_code):
                return block_code
        return None

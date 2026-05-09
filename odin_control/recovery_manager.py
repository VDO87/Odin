from __future__ import annotations

from dataclasses import dataclass

from odin_control.state_machine import OdinState, OdinStateMachine


@dataclass(slots=True)
class RecoveryResult:
    accepted: bool
    state: OdinState
    details: str


class RecoveryManager:
    def __init__(self, machine: OdinStateMachine) -> None:
        self.machine = machine

    def handle_network_failure(self) -> RecoveryResult:
        result = self.machine.transition(OdinState.DEGRADED_NETWORK, reason="network_failure")
        return RecoveryResult(result.accepted, self.machine.state, result.reason)

    def begin_recovery(self) -> RecoveryResult:
        result = self.machine.transition(OdinState.RECOVERY_MODE, reason="network_recovered")
        return RecoveryResult(result.accepted, self.machine.state, result.reason)

    def after_healthcheck(self, ok: bool) -> RecoveryResult:
        target = OdinState.POSITION_RECONCILIATION if ok else OdinState.BLOCKED
        result = self.machine.transition(target, reason="recovery_healthcheck")
        return RecoveryResult(result.accepted, self.machine.state, result.reason)

    def after_reconciliation(self, ok: bool) -> RecoveryResult:
        target = OdinState.READY if ok else OdinState.BLOCKED
        result = self.machine.transition(target, reason="recovery_reconciliation")
        return RecoveryResult(result.accepted, self.machine.state, result.reason)

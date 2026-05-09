from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OdinState(StrEnum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    HEALTHCHECK = "HEALTHCHECK"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DEGRADED_NETWORK = "DEGRADED_NETWORK"
    RECOVERY_MODE = "RECOVERY_MODE"
    POSITION_RECONCILIATION = "POSITION_RECONCILIATION"
    BLOCKED = "BLOCKED"
    KILLED = "KILLED"


ALLOWED_TRANSITIONS: dict[OdinState, set[OdinState]] = {
    OdinState.STOPPED: {OdinState.STARTING, OdinState.KILLED},
    OdinState.STARTING: {OdinState.HEALTHCHECK, OdinState.BLOCKED, OdinState.KILLED},
    OdinState.HEALTHCHECK: {OdinState.READY, OdinState.BLOCKED, OdinState.KILLED},
    OdinState.READY: {OdinState.RUNNING, OdinState.PAUSED, OdinState.BLOCKED, OdinState.KILLED},
    OdinState.RUNNING: {
        OdinState.PAUSED,
        OdinState.DEGRADED_NETWORK,
        OdinState.POSITION_RECONCILIATION,
        OdinState.BLOCKED,
        OdinState.KILLED,
        OdinState.STOPPED,
    },
    OdinState.PAUSED: {OdinState.RUNNING, OdinState.STOPPED, OdinState.KILLED, OdinState.BLOCKED},
    OdinState.DEGRADED_NETWORK: {OdinState.RECOVERY_MODE, OdinState.BLOCKED, OdinState.KILLED},
    OdinState.RECOVERY_MODE: {OdinState.HEALTHCHECK, OdinState.POSITION_RECONCILIATION, OdinState.BLOCKED, OdinState.KILLED},
    OdinState.POSITION_RECONCILIATION: {OdinState.READY, OdinState.BLOCKED, OdinState.KILLED},
    OdinState.BLOCKED: {OdinState.HEALTHCHECK, OdinState.RECOVERY_MODE, OdinState.KILLED, OdinState.STOPPED},
    OdinState.KILLED: {OdinState.STOPPED},
}


@dataclass(slots=True)
class TransitionResult:
    accepted: bool
    from_state: OdinState
    to_state: OdinState
    reason: str


class OdinStateMachine:
    def __init__(self, initial: OdinState = OdinState.STOPPED) -> None:
        self._state = initial

    @property
    def state(self) -> OdinState:
        return self._state

    def can_transition(self, target: OdinState) -> bool:
        return target in ALLOWED_TRANSITIONS[self._state]

    def transition(self, target: OdinState, *, reason: str = "") -> TransitionResult:
        if not self.can_transition(target):
            return TransitionResult(
                accepted=False,
                from_state=self._state,
                to_state=target,
                reason=reason or "invalid_transition",
            )
        previous = self._state
        self._state = target
        return TransitionResult(
            accepted=True,
            from_state=previous,
            to_state=target,
            reason=reason or "ok",
        )

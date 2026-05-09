from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from odin_control.permissions import PermissionManager
from odin_control.state_machine import OdinState
from odin_logs.audit import AuditLogger
from odin_logs.schemas import make_id


SUPPORTED_COMMANDS = {
    "START_ODIN",
    "PAUSE_ODIN",
    "RESUME_ODIN",
    "STOP_ODIN",
    "KILL_SWITCH",
    "RUN_HEALTHCHECK",
    "SYNC_MT5_POSITIONS",
    "RELOAD_CONFIG",
    "MT5_STATUS",
    "MT5_HEALTHCHECK",
    "MT5_SYNC_POSITIONS",
    "MT5_LIST_POSITIONS",
    "MT5_LIST_SYMBOLS",
    "MT5_GET_TICK",
    "MT5_GET_CANDLES",
    "ENABLE_REAL_TRADING",
    "DISABLE_RISK_ENGINE",
    "DIRECT_ORDER_SEND",
    "DELETE_LOGS",
    "IGNORE_POSITION_RECONCILIATION",
    "MT5_ORDER_SEND",
    "MT5_CLOSE_POSITION",
    "MT5_MODIFY_POSITION",
    "MT5_ENABLE_REAL_TRADING",
}


@dataclass(slots=True)
class CommandRequest:
    command: str
    actor: str = "operator"
    role: str = "operator"
    payload: dict[str, Any] = field(default_factory=dict)
    confirmation: bool = False


@dataclass(slots=True)
class CommandResult:
    command_id: str
    command: str
    accepted: bool
    state: OdinState
    reason: str
    data: dict[str, Any] = field(default_factory=dict)


class CommandBus:
    def __init__(
        self,
        *,
        get_state: Callable[[], OdinState],
        permissions: PermissionManager,
        audit: AuditLogger,
        handlers: dict[str, Callable[[CommandRequest], dict[str, Any]]],
    ) -> None:
        self.get_state = get_state
        self.permissions = permissions
        self.audit = audit
        self.handlers = handlers

    def execute(self, request: CommandRequest) -> CommandResult:
        command_id = make_id("cmd")
        command = request.command.strip().upper()

        if command not in SUPPORTED_COMMANDS:
            result = CommandResult(command_id, command, False, self.get_state(), "unsupported_command")
            self.audit.record("command", actor=request.actor, result="rejected", data=asdict(result))
            return result

        decision = self.permissions.check(command, role=request.role)
        if not decision.allowed:
            result = CommandResult(command_id, command, False, self.get_state(), decision.reason)
            self.audit.record("command", actor=request.actor, result="rejected", data=asdict(result))
            return result

        handler = self.handlers.get(command)
        if handler is None:
            result = CommandResult(command_id, command, False, self.get_state(), "handler_not_configured")
            self.audit.record("command", actor=request.actor, result="rejected", data=asdict(result))
            return result

        payload = handler(request)
        accepted = bool(payload.get("accepted", True))
        reason = str(payload.get("reason", "ok" if accepted else "rejected"))
        result = CommandResult(command_id, command, accepted, self.get_state(), reason, data=payload)
        self.audit.record("command", actor=request.actor, result="accepted" if accepted else "rejected", data=asdict(result))
        return result

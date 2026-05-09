from __future__ import annotations

from dataclasses import dataclass


CRITICAL_COMMANDS = {"PAUSE_ODIN", "RESUME_ODIN", "STOP_ODIN", "KILL_SWITCH"}
BLOCKED_COMMANDS = {
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
class AssistantPermission:
    allowed: bool
    reason: str
    confirmation_required: bool = False


class AssistantPermissionGuard:
    def check(self, command: str) -> AssistantPermission:
        if command in BLOCKED_COMMANDS:
            return AssistantPermission(False, "dangerous_command_blocked", False)
        if command in CRITICAL_COMMANDS:
            return AssistantPermission(True, "confirmation_required", True)
        return AssistantPermission(True, "allowed", False)

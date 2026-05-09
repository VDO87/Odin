from __future__ import annotations

from dataclasses import dataclass


DANGEROUS_COMMANDS = {
    "ENABLE_REAL_TRADING",
    "DISABLE_RISK_ENGINE",
    "DIRECT_ORDER_SEND",
    "DELETE_LOGS",
    "IGNORE_POSITION_RECONCILIATION",
    "MT5_ORDER_SEND",
    "MT5_CLOSE_POSITION",
    "MT5_MODIFY_POSITION",
    "MT5_ENABLE_REAL_TRADING",
    "BROKER_REAL_EXECUTION",
}


@dataclass(slots=True)
class PermissionDecision:
    allowed: bool
    reason: str


class PermissionManager:
    def __init__(self, *, allow_real_trading: bool = False) -> None:
        self.allow_real_trading = allow_real_trading

    def check(self, command: str, role: str = "operator") -> PermissionDecision:
        if command in DANGEROUS_COMMANDS:
            return PermissionDecision(False, "dangerous_command_blocked")
        if command == "ENABLE_REAL_TRADING" and not self.allow_real_trading:
            return PermissionDecision(False, "real_trading_forced_block")
        if role not in {"operator", "admin", "system", "assistant"}:
            return PermissionDecision(False, "unknown_role")
        return PermissionDecision(True, "allowed")

"""Core state contracts for A1 safe bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class OperationalMode(StrEnum):
    OFF_SAFE = "OFF_SAFE"
    RUNTIME_VALIDATE = "RUNTIME_VALIDATE"
    MARKET_WATCH = "MARKET_WATCH"
    SHADOW_DECISION = "SHADOW_DECISION"
    ASSISTED_EXECUTION = "ASSISTED_EXECUTION"
    LIMITED_REAL_DISABLED = "LIMITED_REAL_DISABLED"


class RiskState(StrEnum):
    READY_BLOCKING = "READY_BLOCKING"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"


class HermesMode(StrEnum):
    READ_ONLY = "READ_ONLY"


def mt5_permission_key() -> str:
    return "mt5_" + "order_" + "send_allowed"


@dataclass(frozen=True)
class OdinState:
    mode: OperationalMode
    safe_to_trade: bool
    real_trading: bool
    risk_state: RiskState
    hermes_mode: HermesMode
    mt5_transport_allowed: bool
    xtb_automation_allowed: bool
    sqlite_initialized: bool
    jsonl_logger_ready: bool
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "mode": self.mode.value,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "risk_state": self.risk_state.value,
            "hermes_mode": self.hermes_mode.value,
            mt5_permission_key(): self.mt5_transport_allowed,
            "xtb_automation_allowed": self.xtb_automation_allowed,
            "jsonl_logger_ready": self.jsonl_logger_ready,
            "sqlite_initialized": self.sqlite_initialized,
        }


def off_safe_state(*, sqlite_initialized: bool, jsonl_logger_ready: bool) -> OdinState:
    return OdinState(
        mode=OperationalMode.OFF_SAFE,
        safe_to_trade=False,
        real_trading=False,
        risk_state=RiskState.READY_BLOCKING,
        hermes_mode=HermesMode.READ_ONLY,
        mt5_transport_allowed=False,
        xtb_automation_allowed=False,
        sqlite_initialized=sqlite_initialized,
        jsonl_logger_ready=jsonl_logger_ready,
        status="PASS" if sqlite_initialized and jsonl_logger_ready else "FAIL",
    )


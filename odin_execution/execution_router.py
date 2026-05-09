from __future__ import annotations

from pathlib import Path
from typing import Any

from odin_logs.logger import JsonlLogger


class ExecutionRouter:
    def __init__(self, *, allow_real_execution: bool = False, log_root: str | Path = "logs") -> None:
        self.allow_real_execution = bool(allow_real_execution)
        self.audit = JsonlLogger(Path(log_root) / "trading" / "execution_audit.log")

    def route(self, order: dict[str, Any], *, venue: str = "MT5") -> dict[str, Any]:
        if not self.allow_real_execution:
            payload = {
                "accepted": False,
                "reason": "real_execution_blocked_rc1",
                "venue": venue,
                "order": order,
            }
            self.audit.write("execution_blocked", payload)
            return payload
        payload = {"accepted": False, "reason": "rc1_forces_shadow_only", "venue": venue, "order": order}
        self.audit.write("execution_blocked", payload)
        return payload

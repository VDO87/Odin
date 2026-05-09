from __future__ import annotations

from pathlib import Path
from typing import Any

from odin_health.checks_llm import check_local_llm
from odin_health.checks_market_apis import check_market_apis
from odin_health.checks_mt5 import check_mt5
from odin_health.checks_network import check_network
from odin_health.checks_system import check_system
from odin_health.checks_telegram import check_telegram
from odin_logs.logger import JsonlLogger


STATUS_ORDER = {"OK": 0, "WARNING": 1, "CRITICAL": 2, "BLOCKED": 3}


class OdinHealthcheck:
    def __init__(self, log_root: str | Path = "logs") -> None:
        self.logger = JsonlLogger(Path(log_root) / "health" / "healthcheck.log")

    def run(self) -> dict[str, Any]:
        checks = {
            "network": check_network(),
            "system": check_system(),
            "mt5": check_mt5(),
            "telegram": check_telegram(),
            "local_llm": check_local_llm(),
            "market_apis": check_market_apis(),
        }

        worst = "OK"
        for payload in checks.values():
            status = str(payload.get("status", "OK"))
            if STATUS_ORDER[status] > STATUS_ORDER[worst]:
                worst = status

        if worst == "CRITICAL":
            overall = "BLOCKED"
        else:
            overall = worst

        result = {"status": overall, "checks": checks}
        self.logger.write("healthcheck", result)
        return result

from __future__ import annotations

from odin_control.system_controller import SystemController
from odin_health.healthcheck import OdinHealthcheck


class OdinRuntime:
    def __init__(self) -> None:
        self.controller = SystemController(log_root="logs")
        self.health = OdinHealthcheck(log_root="logs")

    def start(self) -> dict[str, object]:
        return self.controller.execute("START_ODIN", actor="runtime", role="system")

    def healthcheck(self) -> dict[str, object]:
        return self.health.run()

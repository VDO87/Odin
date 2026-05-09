from __future__ import annotations

from pathlib import Path
from typing import Any

from odin_control.system_controller import SystemController
from odin_core.orchestrator import ShadowRuntimeOrchestrator


class OdinRuntime:
    def __init__(self, controller: SystemController | None = None, *, log_root: str | Path = "logs") -> None:
        self.controller = controller or SystemController(log_root=log_root)
        self.orchestrator = ShadowRuntimeOrchestrator(self.controller, log_root=log_root)

    def start(self) -> dict[str, Any]:
        return self.orchestrator.start()

    def stop(self) -> dict[str, Any]:
        return self.orchestrator.stop()

    def pause(self) -> dict[str, Any]:
        return self.orchestrator.pause()

    def resume(self) -> dict[str, Any]:
        return self.orchestrator.resume()

    def run_once(self) -> dict[str, Any]:
        return self.orchestrator.run_once()

    def run_loop(self) -> dict[str, Any]:
        return self.orchestrator.run_loop()

    def safe_shutdown(self) -> dict[str, Any]:
        return self.orchestrator.safe_shutdown()

    def get_status(self) -> dict[str, Any]:
        return self.orchestrator.get_status()

    def snapshot(self) -> dict[str, Any]:
        return self.orchestrator.snapshot()

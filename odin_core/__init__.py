from __future__ import annotations

from typing import Any

__all__ = ["OdinRuntime", "RuntimeState", "RuntimeStatus"]


def __getattr__(name: str) -> Any:
    if name == "OdinRuntime":
        from odin_core.runtime import OdinRuntime

        return OdinRuntime
    if name in {"RuntimeState", "RuntimeStatus"}:
        from odin_core.runtime_state import RuntimeState, RuntimeStatus

        return {"RuntimeState": RuntimeState, "RuntimeStatus": RuntimeStatus}[name]
    raise AttributeError(name)

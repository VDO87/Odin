from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(slots=True)
class AssistantContext:
    payload: dict[str, Any]


class ContextBuilder:
    def __init__(self, providers: dict[str, Callable[[], dict[str, Any]]] | None = None) -> None:
        self.providers = providers or {}

    def build(self) -> AssistantContext:
        data: dict[str, Any] = {}
        for name, provider in self.providers.items():
            try:
                data[name] = provider()
            except Exception as error:
                data[name] = {"error": f"{error.__class__.__name__}: {error}"}
        return AssistantContext(payload=data)

from __future__ import annotations

from typing import Any

from odin_brain.local_llm import LocalLLMRuntime


class LocalLLMInterface:
    def __init__(self) -> None:
        self.runtime = LocalLLMRuntime()

    def is_enabled(self) -> bool:
        return self.runtime.is_enabled()

    def healthcheck(self) -> dict[str, Any]:
        return self.runtime.healthcheck()

    def list_models(self) -> dict[str, Any]:
        return self.runtime.list_models()

    def generate_response(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.runtime.generate_response(prompt, context=context, options=options)

    def summarize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.summarize_context(context)

    def explain_decision(self, decision_packet: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.explain_decision(decision_packet)

    def safe_answer(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        return self.runtime.safe_answer(question, context)

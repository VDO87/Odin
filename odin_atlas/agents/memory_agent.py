from __future__ import annotations

from typing import Any

from odin_assistant.local_llm_interface import LocalLLMInterface


class MemoryAgent:
    def __init__(self) -> None:
        self.llm = LocalLLMInterface()

    def analyze(self, context: dict[str, object]) -> dict[str, object]:
        memory_context: dict[str, Any] = {
            "symbol": context.get("symbol", "UNKNOWN"),
            "timeframe": context.get("timeframe", "M15"),
            "mt5": context.get("mt5", {}),
            "risk": context.get("risk", {}),
        }
        result = self.llm.safe_answer(
            "Gera uma nota operacional curta com lição aprendida para memória do ODIN.",
            memory_context,
        )
        if result.get("status") == "OK":
            return {
                "score": 0.6,
                "result": str(result.get("response", "MEMORY_CONTEXT_OK")),
                "source": "local_llm",
                "fallback_used": False,
            }
        return {
            "score": 0.5,
            "result": "MEMORY_FALLBACK: sem LLM local disponível",
            "source": "fallback",
            "fallback_used": True,
            "error": result.get("error"),
        }

from __future__ import annotations

from typing import Any

from odin_assistant.local_llm_interface import LocalLLMInterface


class CriticAgent:
    def __init__(self) -> None:
        self.llm = LocalLLMInterface()

    def analyze(self, context: dict[str, object]) -> dict[str, object]:
        critic_context: dict[str, Any] = {
            "symbol": context.get("symbol", "UNKNOWN"),
            "timeframe": context.get("timeframe", "M15"),
            "risk": context.get("risk", {}),
            "atlas": context.get("atlas", {}),
        }
        result = self.llm.safe_answer(
            "Resume o risco e inconsistências principais desta análise ATLAS.",
            critic_context,
        )
        if result.get("status") == "OK":
            return {
                "score": 1.0,
                "result": str(result.get("response", "CRITIC_OK")),
                "source": "local_llm",
                "fallback_used": False,
            }
        return {
            "score": 0.8,
            "result": "CRITIC_FALLBACK: sem LLM local disponível",
            "source": "fallback",
            "fallback_used": True,
            "error": result.get("error"),
        }

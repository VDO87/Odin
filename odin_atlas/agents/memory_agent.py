from __future__ import annotations


class MemoryAgent:
    def analyze(self, context: dict[str, object]) -> dict[str, object]:
        return {"score": 0.5, "result": "MEMORY_CONTEXT_OK"}

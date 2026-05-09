from __future__ import annotations


class ExecutionAgent:
    def analyze(self, context: dict[str, object]) -> dict[str, object]:
        return {"score": 0.0, "result": "SHADOW_ONLY"}

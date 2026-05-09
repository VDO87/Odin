from __future__ import annotations


class CriticAgent:
    def analyze(self, context: dict[str, object]) -> dict[str, object]:
        return {"score": 1.0, "result": "CRITIC_OK"}

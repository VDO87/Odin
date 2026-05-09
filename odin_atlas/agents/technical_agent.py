from __future__ import annotations


class TechnicalAgent:
    def analyze(self, context: dict[str, object]) -> dict[str, object]:
        return {"score": 0.6, "result": "TECH_NEUTRAL"}

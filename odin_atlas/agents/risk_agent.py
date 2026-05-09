from __future__ import annotations


class RiskAgent:
    def analyze(self, context: dict[str, object]) -> dict[str, object]:
        return {"score": 1.0, "result": "RISK_CHECK_REQUIRED"}

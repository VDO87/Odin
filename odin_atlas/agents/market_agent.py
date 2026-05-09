from __future__ import annotations


class MarketAgent:
    def analyze(self, context: dict[str, object]) -> dict[str, object]:
        return {"score": 0.6, "result": "MARKET_NEUTRAL"}

from __future__ import annotations


class NewsAgent:
    def analyze(self, context: dict[str, object]) -> dict[str, object]:
        return {"score": 0.5, "result": "NEWS_NEUTRAL"}

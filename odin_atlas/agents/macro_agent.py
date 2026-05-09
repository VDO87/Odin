from __future__ import annotations


class MacroAgent:
    def analyze(self, context: dict[str, object]) -> dict[str, object]:
        return {"score": 0.5, "result": "MACRO_NEUTRAL"}

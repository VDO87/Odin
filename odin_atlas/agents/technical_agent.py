from __future__ import annotations

from typing import Any


class TechnicalAgent:
    def analyze(self, context: dict[str, Any]) -> dict[str, object]:
        mt5 = context.get("mt5", {}) if isinstance(context.get("mt5", {}), dict) else {}
        candles = mt5.get("candles", []) if isinstance(mt5.get("candles", []), list) else []

        if len(candles) < 2:
            return {
                "score": 0.45,
                "result": "TECH_INSUFFICIENT_DATA",
                "trend": "unknown",
                "volatility": 0.0,
                "range": 0.0,
            }

        closes = [float(c.get("close", 0.0) or 0.0) for c in candles]
        highs = [float(c.get("high", 0.0) or 0.0) for c in candles]
        lows = [float(c.get("low", 0.0) or 0.0) for c in candles]

        trend = "up" if closes[-1] > closes[0] else "down" if closes[-1] < closes[0] else "flat"
        candle_range = max(highs) - min(lows)
        avg_close = sum(closes) / len(closes)
        volatility = (candle_range / avg_close) if avg_close > 0 else 0.0

        score = 0.55
        if trend == "up":
            score = 0.62
        elif trend == "down":
            score = 0.5
        if volatility > 0.02:
            score -= 0.1

        return {
            "score": max(0.0, min(1.0, score)),
            "result": "TECH_ANALYZED",
            "trend": trend,
            "volatility": round(volatility, 6),
            "range": round(candle_range, 6),
        }

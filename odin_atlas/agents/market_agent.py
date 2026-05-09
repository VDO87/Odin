from __future__ import annotations

from typing import Any


class MarketAgent:
    def analyze(self, context: dict[str, Any]) -> dict[str, object]:
        mt5 = context.get("mt5", {}) if isinstance(context.get("mt5", {}), dict) else {}
        tick = mt5.get("tick", {}) if isinstance(mt5.get("tick", {}), dict) else {}
        spread_points = float(mt5.get("spread_points", 0.0) or 0.0)
        bid = float(tick.get("bid", 0.0) or 0.0)
        ask = float(tick.get("ask", 0.0) or 0.0)

        score = 0.6
        signals: list[str] = ["MARKET_NEUTRAL"]

        if bid > 0 and ask > 0:
            score = 0.65
            signals.append("TICK_AVAILABLE")
        if spread_points > 30:
            score = 0.35
            signals.append("SPREAD_HIGH")

        return {
            "score": max(0.0, min(1.0, score)),
            "result": ",".join(signals),
            "symbol": context.get("symbol", "UNKNOWN"),
            "timeframe": mt5.get("timeframe", context.get("timeframe", "M15")),
            "spread_points": spread_points,
        }

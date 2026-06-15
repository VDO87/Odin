"""Deterministic mock candles."""

from __future__ import annotations

from odin.contracts.market_data import Candle


def eurusd_m15_candles() -> list[Candle]:
    return [
        Candle("EURUSD", "M15", "2026-06-15T08:00:00+00:00", 1.08420, 1.08480, 1.08400, 1.08470, 120, 0.00008),
        Candle("EURUSD", "M15", "2026-06-15T08:15:00+00:00", 1.08470, 1.08510, 1.08450, 1.08490, 118, 0.00008),
        Candle("EURUSD", "M15", "2026-06-15T08:30:00+00:00", 1.08490, 1.08520, 1.08460, 1.08500, 125, 0.00008),
        Candle("EURUSD", "M15", "2026-06-15T08:45:00+00:00", 1.08500, 1.08525, 1.08485, 1.08505, 121, 0.00008),
        Candle("EURUSD", "M15", "2026-06-15T09:00:00+00:00", 1.08505, 1.08512, 1.08492, 1.08500, 119, 0.00008),
    ]


def candles_for(symbol: str, timeframe: str) -> list[Candle]:
    if symbol == "EURUSD" and timeframe == "M15":
        return eurusd_m15_candles()
    return []


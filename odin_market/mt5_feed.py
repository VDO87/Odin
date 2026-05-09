from __future__ import annotations

from pathlib import Path
from typing import Any

from odin_execution.mt5_shadow import MT5ShadowAdapter
from odin_logs.logger import JsonlLogger


class MT5Feed:
    def __init__(self, adapter: MT5ShadowAdapter | None = None, *, log_root: str | Path = "logs") -> None:
        self.adapter = adapter or MT5ShadowAdapter()
        self.log = JsonlLogger(Path(log_root) / "market" / "mt5_feed.log")

    def get_tick(self, symbol: str) -> dict[str, Any]:
        result = self.adapter.get_tick(symbol)
        self.log.write("mt5_tick", {"symbol": symbol, "status": result.get("status")})
        return result

    def get_candles(self, symbol: str, timeframe: str, count: int) -> dict[str, Any]:
        result = self.adapter.get_candles(symbol, timeframe, count)
        self.log.write(
            "mt5_candles",
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "count": count,
                "status": result.get("status"),
            },
        )
        return result

    def get_symbols(self) -> dict[str, Any]:
        result = self.adapter.get_symbols()
        self.log.write("mt5_symbols", {"status": result.get("status")})
        return result

from __future__ import annotations

import os
from typing import Any


def check_market_apis() -> dict[str, Any]:
    keys = {
        "TRADING_ECONOMICS_API_KEY": bool(os.getenv("TRADING_ECONOMICS_API_KEY", "").strip()),
        "FINNHUB_API_KEY": bool(os.getenv("FINNHUB_API_KEY", "").strip()),
        "ALPHA_VANTAGE_API_KEY": bool(os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()),
        "NEWSAPI_KEY": bool(os.getenv("NEWSAPI_KEY", "").strip()),
    }

    configured_count = sum(1 for value in keys.values() if value)
    status = "OK" if configured_count > 0 else "WARNING"

    return {
        "status": status,
        "configured_count": configured_count,
        "keys": keys,
    }

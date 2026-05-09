from __future__ import annotations

import os
from typing import Any


def build_security_badges() -> dict[str, Any]:
    trading_real_blocked = os.getenv("ENABLE_REAL_TRADING", "false").lower() != "true"
    mt5_order_send_blocked = os.getenv("MT5_ORDER_SEND_ENABLED", "false").lower() != "true"
    broker_real_blocked = os.getenv("BROKER_ALLOW_REAL_EXECUTION", "false").lower() != "true"
    xtb_real_blocked = os.getenv("XTB_REAL_ENABLED", "false").lower() != "true"
    return {
        "TRADING REAL": "BLOCKED" if trading_real_blocked else "UNSAFE",
        "MT5 ORDER_SEND": "BLOCKED" if mt5_order_send_blocked else "UNSAFE",
        "BROKER REAL": "BLOCKED" if broker_real_blocked else "UNSAFE",
        "XTB REAL": "BLOCKED" if xtb_real_blocked else "UNSAFE",
        "ATLAS EXECUTION": "SHADOW_ONLY",
        "LLM EXECUTION": "READ_ONLY",
    }

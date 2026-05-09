from __future__ import annotations

import os
from typing import Any


def check_mt5() -> dict[str, Any]:
    enabled = os.getenv("MT5_ENABLED", "true").lower() == "true"
    shadow_mode = os.getenv("MT5_SHADOW_MODE", "true").lower() == "true"
    order_send = os.getenv("MT5_ORDER_SEND_ENABLED", "false").lower() == "true"

    try:
        import MetaTrader5 as _mt5  # type: ignore  # noqa: F401

        lib_available = True
    except Exception:
        lib_available = False

    status = "OK"
    if enabled and not lib_available:
        status = "WARNING"
    if order_send:
        status = "CRITICAL"

    return {
        "status": status,
        "enabled": enabled,
        "shadow_mode": shadow_mode,
        "order_send_enabled": order_send,
        "library_available": lib_available,
    }

from __future__ import annotations

import os
from typing import Any

from odin_execution.mt5_shadow import MT5ShadowAdapter
from odin_execution.position_reconciler import PositionReconciler
from odin_execution.position_registry import PositionRegistry


def _mode_requires_mt5() -> bool:
    mode = os.getenv("ODIN_MODE", "SHADOW_MT5").strip().upper()
    return mode == "SHADOW_MT5"


def check_mt5() -> dict[str, Any]:
    enabled = os.getenv("MT5_ENABLED", "true").lower() == "true"
    shadow_mode = os.getenv("MT5_SHADOW_MODE", "true").lower() == "true"
    order_send = os.getenv("MT5_ORDER_SEND_ENABLED", "false").lower() == "true"
    symbols_raw = os.getenv("MT5_SYMBOLS", "EURUSD")
    symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
    odin_magic = int(os.getenv("MT5_MAGIC_NUMBER_ODIN", "870087"))

    adapter = MT5ShadowAdapter(order_send_enabled=order_send)

    if not enabled:
        return {
            "status": "WARNING",
            "enabled": enabled,
            "shadow_mode": shadow_mode,
            "order_send_enabled": order_send,
            "library_available": adapter.is_available(),
            "message": "MT5 desactivado por configuração.",
            "safe_to_trade": False,
        }

    if order_send:
        return {
            "status": "CRITICAL",
            "enabled": enabled,
            "shadow_mode": shadow_mode,
            "order_send_enabled": order_send,
            "library_available": adapter.is_available(),
            "message": "MT5 order_send está activado, o que viola RC1.2.",
            "safe_to_trade": False,
        }

    if not adapter.is_available():
        status = "BLOCKED" if _mode_requires_mt5() else "WARNING"
        return {
            "status": status,
            "enabled": enabled,
            "shadow_mode": shadow_mode,
            "order_send_enabled": order_send,
            "library_available": False,
            "message": "Biblioteca MetaTrader5 indisponível neste ambiente.",
            "safe_to_trade": False,
            "symbols_configured": symbols,
        }

    init = adapter.initialize()
    if init["status"] != "OK":
        status = "BLOCKED" if _mode_requires_mt5() else "WARNING"
        return {
            "status": status,
            "enabled": enabled,
            "shadow_mode": shadow_mode,
            "order_send_enabled": order_send,
            "library_available": True,
            "message": init["message"],
            "safe_to_trade": False,
            "init": init,
            "symbols_configured": symbols,
        }

    terminal = adapter.get_terminal_info()
    account = adapter.get_account_info()
    symbols_result = adapter.get_symbols()

    tick_ok = False
    tick_samples: dict[str, Any] = {}
    for symbol in symbols:
        tick = adapter.get_tick(symbol)
        tick_samples[symbol] = {"status": tick.get("status"), "message": tick.get("message")}
        if tick.get("status") == "OK":
            tick_ok = True

    positions_result = adapter.get_positions()
    positions = list(positions_result.get("data", {}).get("positions", []))
    registry = PositionRegistry(odin_magic=odin_magic)
    reconciler = PositionReconciler(registry, odin_magic=odin_magic)
    reconciliation = reconciler.reconcile(positions)

    status = "OK"
    safe_to_trade = True
    message = "MT5 shadow saudável."

    if not tick_ok:
        status = "WARNING"
        safe_to_trade = False
        message = "Sem tick válido para símbolos configurados."

    if not reconciliation.get("safe_to_trade", False):
        status = "BLOCKED"
        safe_to_trade = False
        message = "Reconcialiação MT5 detectou bloqueios."

    if _mode_requires_mt5() and status in {"WARNING", "BLOCKED"}:
        status = "BLOCKED"
        safe_to_trade = False

    return {
        "status": status,
        "enabled": enabled,
        "shadow_mode": shadow_mode,
        "order_send_enabled": order_send,
        "library_available": True,
        "message": message,
        "safe_to_trade": safe_to_trade,
        "symbols_configured": symbols,
        "terminal": terminal,
        "account": account,
        "symbols_available": symbols_result,
        "tick_samples": tick_samples,
        "positions_result": positions_result,
        "reconciliation": reconciliation,
    }

from __future__ import annotations

from typing import Any


class MT5ShadowAdapter:
    def __init__(self, *, order_send_enabled: bool = False) -> None:
        self.order_send_enabled = bool(order_send_enabled)
        self.available = False
        self._mt5: Any | None = None
        try:
            import MetaTrader5 as mt5  # type: ignore

            self._mt5 = mt5
            self.available = True
        except Exception:
            self.available = False

    def healthcheck(self) -> dict[str, Any]:
        return {
            "status": "OK" if self.available else "WARNING",
            "available": self.available,
            "shadow_mode": True,
            "order_send_enabled": self.order_send_enabled,
        }

    def get_positions(self) -> list[dict[str, Any]]:
        if not self.available:
            return []
        positions = self._mt5.positions_get()  # type: ignore[union-attr]
        if positions is None:
            return []
        return [p._asdict() for p in positions]

    def send_order(self, order: dict[str, Any]) -> dict[str, Any]:
        return {
            "accepted": False,
            "reason": "mt5_shadow_mode_order_send_blocked",
            "order": order,
        }

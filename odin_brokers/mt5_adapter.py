from __future__ import annotations

from typing import Any

from odin_brokers.base import BrokerAdapterBase
from odin_execution.mt5_shadow import MT5ShadowAdapter


class MT5Adapter(BrokerAdapterBase):
    name = "MT5"

    def __init__(self) -> None:
        self.shadow = MT5ShadowAdapter(order_send_enabled=False)

    def connect(self) -> dict[str, Any]:
        return {"ok": self.shadow.available, "broker": self.name, "shadow_mode": True}

    def disconnect(self) -> dict[str, Any]:
        return {"ok": True, "broker": self.name}

    def healthcheck(self) -> dict[str, Any]:
        payload = self.shadow.healthcheck()
        payload["broker"] = self.name
        return payload

    def get_account_status(self) -> dict[str, Any]:
        return {"broker": self.name, "shadow_mode": True, "available": self.shadow.available}

    def get_positions(self) -> list[dict[str, Any]]:
        return self.shadow.get_positions()

    def get_orders(self) -> list[dict[str, Any]]:
        return []

    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        return self.shadow.send_order(order)

    def close_order(self, order_id: str) -> dict[str, Any]:
        return {"accepted": False, "reason": "mt5_shadow_close_blocked", "order_id": order_id}

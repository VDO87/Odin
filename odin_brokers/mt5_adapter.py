from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from odin_brokers.base import BrokerAdapterBase
from odin_execution.mt5_shadow import MT5ShadowAdapter


class MT5Adapter(BrokerAdapterBase):
    name = "MT5"

    def __init__(self) -> None:
        self.shadow = MT5ShadowAdapter(order_send_enabled=False)

    def connect(self) -> dict[str, Any]:
        return self.shadow.initialize()

    def disconnect(self) -> dict[str, Any]:
        return self.shadow.shutdown()

    def healthcheck(self) -> dict[str, Any]:
        payload = self.shadow.healthcheck()
        payload["data"]["broker"] = self.name
        return payload

    def get_account_status(self) -> dict[str, Any]:
        return self.shadow.get_account_info()

    def get_positions(self) -> list[dict[str, Any]]:
        result = self.shadow.get_positions()
        return list(result.get("data", {}).get("positions", []))

    def get_orders(self) -> list[dict[str, Any]]:
        result = self.shadow.get_orders()
        return list(result.get("data", {}).get("orders", []))

    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        return self.shadow.place_order(order)

    def close_order(self, order_id: str) -> dict[str, Any]:
        return {
            "status": "BLOCKED",
            "message": "Fecho de posições MT5 bloqueado em RC1.2 Shadow Mode.",
            "data": {"order_id": order_id},
            "safe_to_trade": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

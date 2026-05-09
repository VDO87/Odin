from __future__ import annotations

from typing import Any

from odin_brokers.base import BrokerAdapterBase


class XTBAdapter(BrokerAdapterBase):
    name = "XTB"

    def __init__(self, *, allow_real_execution: bool = False) -> None:
        self.allow_real_execution = allow_real_execution
        self.connected = False

    def connect(self) -> dict[str, Any]:
        self.connected = True
        return {"ok": True, "broker": self.name, "mode": "DEMO_ASSISTED"}

    def disconnect(self) -> dict[str, Any]:
        self.connected = False
        return {"ok": True, "broker": self.name}

    def healthcheck(self) -> dict[str, Any]:
        return {"status": "OK", "broker": self.name, "connected": self.connected}

    def get_account_status(self) -> dict[str, Any]:
        return {"broker": self.name, "connected": self.connected, "account_type": "DEMO"}

    def get_positions(self) -> list[dict[str, Any]]:
        return []

    def get_orders(self) -> list[dict[str, Any]]:
        return []

    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        if not self.allow_real_execution:
            return {"accepted": False, "reason": "real_execution_blocked", "broker": self.name, "order": order}
        return {"accepted": False, "reason": "rc1_blocked", "broker": self.name, "order": order}

    def close_order(self, order_id: str) -> dict[str, Any]:
        return {"accepted": False, "reason": "rc1_blocked", "broker": self.name, "order_id": order_id}

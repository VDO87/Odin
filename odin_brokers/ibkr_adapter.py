from __future__ import annotations

from typing import Any

from odin_brokers.base import BrokerAdapterBase


class IBKRAdapter(BrokerAdapterBase):
    name = "IBKR"

    def connect(self) -> dict[str, Any]:
        return {"ok": True, "broker": self.name, "mode": "PAPER"}

    def disconnect(self) -> dict[str, Any]:
        return {"ok": True, "broker": self.name}

    def healthcheck(self) -> dict[str, Any]:
        return {"status": "OK", "broker": self.name, "mode": "PAPER"}

    def get_account_status(self) -> dict[str, Any]:
        return {"broker": self.name, "mode": "PAPER"}

    def get_positions(self) -> list[dict[str, Any]]:
        return []

    def get_orders(self) -> list[dict[str, Any]]:
        return []

    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        return {"accepted": False, "reason": "real_execution_blocked", "broker": self.name, "order": order}

    def close_order(self, order_id: str) -> dict[str, Any]:
        return {"accepted": False, "reason": "real_execution_blocked", "broker": self.name, "order_id": order_id}

from __future__ import annotations

from pathlib import Path
from typing import Any

from odin_brokers.base import BrokerAdapterBase
from odin_brokers.ctrader_adapter import CTraderAdapter
from odin_brokers.dukascopy_adapter import DukascopyAdapter
from odin_brokers.ibkr_adapter import IBKRAdapter
from odin_brokers.ig_adapter import IGAdapter
from odin_brokers.mt5_adapter import MT5Adapter
from odin_brokers.saxo_adapter import SaxoAdapter
from odin_brokers.xtb_adapter import XTBAdapter
from odin_logs.logger import JsonlLogger


class BrokerRouter:
    def __init__(self, *, allow_real_execution: bool = False, primary: str = "XTB", log_root: str | Path = "logs") -> None:
        self.allow_real_execution = allow_real_execution
        self.primary = primary.upper()
        self.req_log = JsonlLogger(Path(log_root) / "brokers" / "requests.log")
        self.resp_log = JsonlLogger(Path(log_root) / "brokers" / "responses.log")

        self.adapters: dict[str, BrokerAdapterBase] = {
            "XTB": XTBAdapter(allow_real_execution=allow_real_execution),
            "MT5": MT5Adapter(),
            "IBKR": IBKRAdapter(),
            "IG": IGAdapter(),
            "SAXO": SaxoAdapter(),
            "DUKASCOPY": DukascopyAdapter(),
            "CTRADER": CTraderAdapter(),
        }

    def get_adapter(self, name: str | None = None) -> BrokerAdapterBase:
        resolved = (name or self.primary).upper()
        return self.adapters[resolved]

    def healthcheck(self) -> dict[str, Any]:
        return {name: adapter.healthcheck() for name, adapter in self.adapters.items()}

    def place_order(self, order: dict[str, Any], *, broker: str | None = None) -> dict[str, Any]:
        target = (broker or self.primary).upper()
        self.req_log.write("broker_place_order_request", {"broker": target, "order": order})

        if not self.allow_real_execution:
            payload = {"accepted": False, "reason": "BROKER_ALLOW_REAL_EXECUTION_false", "broker": target, "order": order}
            self.resp_log.write("broker_place_order_response", payload)
            return payload

        result = self.get_adapter(target).place_order(order)
        self.resp_log.write("broker_place_order_response", result)
        return result

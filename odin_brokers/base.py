from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BrokerAdapterBase(ABC):
    name: str

    @abstractmethod
    def connect(self) -> dict[str, Any]: ...

    @abstractmethod
    def disconnect(self) -> dict[str, Any]: ...

    @abstractmethod
    def healthcheck(self) -> dict[str, Any]: ...

    @abstractmethod
    def get_account_status(self) -> dict[str, Any]: ...

    @abstractmethod
    def get_positions(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_orders(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def place_order(self, order: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def close_order(self, order_id: str) -> dict[str, Any]: ...

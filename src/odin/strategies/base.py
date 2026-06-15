"""Base classes for observe-only strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ObserveOnlyStrategy(ABC):
    strategy_mode = "OBSERVE_ONLY"
    read_only = True
    execution_allowed = False
    safe_to_trade = False
    real_trading = False

    @abstractmethod
    def observe(self) -> dict[str, object]:
        raise NotImplementedError


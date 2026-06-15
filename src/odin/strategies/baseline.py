"""Baseline strategy observer with no operational decision."""

from __future__ import annotations

from odin.contracts.strategy import StrategyObservation
from odin.data.quality import data_quality_status
from odin.strategies.base import ObserveOnlyStrategy


class BaselineObserver(ObserveOnlyStrategy):
    strategy_name = "baseline_observer"
    strategy_version = "0.1.0"

    def __init__(
        self,
        *,
        log_path: str = "logs/odin_events.jsonl",
        sqlite_path: str = "runtime/odin.sqlite",
    ) -> None:
        self.log_path = log_path
        self.sqlite_path = sqlite_path

    def observe(self) -> dict[str, object]:
        quality = data_quality_status(log_path=self.log_path, sqlite_path=self.sqlite_path)
        quality_status = str(quality["status"])
        strategy_status = "READY_NO_DECISION" if quality_status == "OK" else "DATA_INVALID"
        observation = StrategyObservation(
            strategy_name=self.strategy_name,
            strategy_version=self.strategy_version,
            strategy_mode=self.strategy_mode,
            strategy_status=strategy_status,
            symbol=str(quality["symbol"]),
            source=str(quality["source"]),
            data_quality_status=quality_status,
            read_only=self.read_only,
            execution_allowed=self.execution_allowed,
            safe_to_trade=self.safe_to_trade,
            real_trading=self.real_trading,
            decision_generated=False,
            proposal_generated=False,
            reason="strategy_baseline_observation_only",
            notes=["Data quality is read before observation status is produced."],
        )
        return observation.to_dict()


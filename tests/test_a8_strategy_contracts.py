import unittest

from odin.contracts.strategy import StrategyObservation


class A8StrategyContractsTests(unittest.TestCase):
    def test_strategy_contract_serializes(self):
        observation = StrategyObservation(
            strategy_name="baseline_observer",
            strategy_version="0.1.0",
            strategy_mode="OBSERVE_ONLY",
            strategy_status="READY_NO_DECISION",
            symbol="EURUSD",
            source="mock",
            data_quality_status="OK",
            read_only=True,
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            decision_generated=False,
            proposal_generated=False,
            reason="strategy_baseline_observation_only",
        ).to_dict()

        self.assertEqual(observation["status"], "OK")
        self.assertEqual(observation["component"], "strategy")
        self.assertEqual(observation["strategy_name"], "baseline_observer")
        self.assertIs(observation["trade_proposal_generated"], False)


if __name__ == "__main__":
    unittest.main()


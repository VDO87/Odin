import tempfile
import unittest
from pathlib import Path

from odin.decision.strategy_status import strategy_status
from odin.strategies.baseline import BaselineObserver


class A8BaselineStrategyTests(unittest.TestCase):
    def _status(self) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            return strategy_status(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

    def test_baseline_strategy_returns_ok(self):
        status = self._status()

        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["component"], "strategy")

    def test_baseline_strategy_observe_only(self):
        self.assertEqual(self._status()["strategy_mode"], "OBSERVE_ONLY")

    def test_baseline_strategy_ready_no_decision(self):
        self.assertEqual(self._status()["strategy_status"], "READY_NO_DECISION")

    def test_baseline_strategy_keeps_safe_to_trade_false(self):
        self.assertIs(self._status()["safe_to_trade"], False)

    def test_baseline_strategy_keeps_real_trading_false(self):
        self.assertIs(self._status()["real_trading"], False)

    def test_baseline_strategy_execution_allowed_false(self):
        self.assertIs(self._status()["execution_allowed"], False)

    def test_baseline_strategy_decision_generated_false(self):
        self.assertIs(self._status()["decision_generated"], False)

    def test_baseline_strategy_trade_proposal_generated_false(self):
        self.assertIs(self._status()["trade_proposal_generated"], False)

    def test_baseline_strategy_uses_mock_source(self):
        self.assertEqual(self._status()["source"], "mock")

    def test_baseline_strategy_reads_data_quality_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = BaselineObserver(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            ).observe()

        self.assertEqual(status["data_quality_status"], "OK")


if __name__ == "__main__":
    unittest.main()


import tempfile
import unittest
from pathlib import Path

from odin.core.smoke import run_runtime_smoke


class A12RuntimeSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _smoke(self):
        return run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_runtime_smoke_returns_pass(self):
        self.assertEqual(self._smoke()["status"], "PASS")

    def test_runtime_smoke_mode_local_safe(self):
        self.assertEqual(self._smoke()["smoke_mode"], "LOCAL_SAFE_SMOKE")

    def test_runtime_smoke_modules_count_at_least_10(self):
        self.assertGreaterEqual(self._smoke()["modules_count"], 10)

    def test_runtime_smoke_all_modules_ok_true(self):
        self.assertIs(self._smoke()["all_modules_ok"], True)

    def test_runtime_smoke_safe_state_confirmed_true(self):
        self.assertIs(self._smoke()["safe_state_confirmed"], True)

    def test_runtime_smoke_blocking_state_confirmed_true(self):
        self.assertIs(self._smoke()["blocking_state_confirmed"], True)

    def test_runtime_smoke_execution_allowed_false(self):
        self.assertIs(self._smoke()["execution_allowed"], False)

    def test_runtime_smoke_safe_to_trade_false(self):
        self.assertIs(self._smoke()["safe_to_trade"], False)

    def test_runtime_smoke_real_trading_false(self):
        self.assertIs(self._smoke()["real_trading"], False)

    def test_runtime_smoke_contains_validate_module(self):
        self.assertIn("validate/core", _module_names(self._smoke()))

    def test_runtime_smoke_contains_hermes_module(self):
        self.assertIn("hermes-summary", _module_names(self._smoke()))

    def test_runtime_smoke_contains_treasury_module(self):
        self.assertIn("treasury-status", _module_names(self._smoke()))

    def test_runtime_smoke_contains_market_module(self):
        self.assertIn("market-status", _module_names(self._smoke()))

    def test_runtime_smoke_contains_market_watch_module(self):
        self.assertIn("market-watch", _module_names(self._smoke()))

    def test_runtime_smoke_contains_data_quality_module(self):
        self.assertIn("data-quality", _module_names(self._smoke()))

    def test_runtime_smoke_contains_strategy_module(self):
        self.assertIn("strategy-status", _module_names(self._smoke()))

    def test_runtime_smoke_contains_decision_intent_module(self):
        self.assertIn("decision-intent", _module_names(self._smoke()))

    def test_runtime_smoke_contains_risk_gate_module(self):
        self.assertIn("risk-gate", _module_names(self._smoke()))

    def test_runtime_smoke_contains_shadow_proposal_module(self):
        self.assertIn("shadow-proposal", _module_names(self._smoke()))


def _module_names(report: dict[str, object]) -> set[str]:
    return {str(module["name"]) for module in report["modules"]}


if __name__ == "__main__":
    unittest.main()

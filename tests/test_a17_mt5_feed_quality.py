import copy
import tempfile
import unittest
from pathlib import Path

from odin.adapters.mt5.feed_quality import mt5_feed_quality_status
from odin.adapters.mt5.market_feed import mt5_market_feed_status
from odin.core.smoke import run_runtime_smoke


class A17MT5FeedQualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _status(self, feed_report=None):
        return mt5_feed_quality_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
            feed_report=feed_report,
        )

    def _feed(self):
        return mt5_market_feed_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_mt5_feed_quality_returns_ok(self):
        self.assertEqual(self._status()["status"], "OK")

    def test_mt5_feed_quality_mode_mock_feed_gates(self):
        self.assertEqual(self._status()["quality_mode"], "MOCK_FEED_GATES")

    def test_mt5_feed_quality_provider_mock(self):
        self.assertEqual(self._status()["provider"], "mt5_mock")

    def test_mt5_feed_quality_source_mock(self):
        self.assertEqual(self._status()["source"], "mt5_mock")

    def test_mt5_feed_quality_symbols_checked_3(self):
        self.assertEqual(self._status()["symbols_checked"], 3)

    def test_mt5_feed_quality_all_ticks_valid_true(self):
        self.assertIs(self._status()["all_ticks_valid"], True)

    def test_mt5_feed_quality_safe_to_use_for_decision_false(self):
        self.assertIs(self._status()["safe_to_use_for_decision"], False)

    def test_mt5_feed_quality_execution_allowed_false(self):
        self.assertIs(self._status()["execution_allowed"], False)

    def test_mt5_feed_quality_safe_to_trade_false(self):
        self.assertIs(self._status()["safe_to_trade"], False)

    def test_mt5_feed_quality_real_trading_false(self):
        self.assertIs(self._status()["real_trading"], False)

    def test_mt5_feed_quality_contains_eurusd_gates(self):
        self.assertIn("EURUSD", _gate_symbols(self._status()))

    def test_mt5_feed_quality_contains_usdjpy_gates(self):
        self.assertIn("USDJPY", _gate_symbols(self._status()))

    def test_mt5_feed_quality_contains_gbpusd_gates(self):
        self.assertIn("GBPUSD", _gate_symbols(self._status()))

    def test_mt5_feed_quality_blocks_invalid_bid(self):
        feed = copy.deepcopy(self._feed())
        feed["ticks"][0]["bid"] = -1.0

        report = self._status(feed)

        self.assertEqual(report["status"], "INVALID")
        self.assertIs(report["all_ticks_valid"], False)
        self.assertEqual(_gate(report, "EURUSD", "bid_positive")["status"], "FAIL")

    def test_mt5_feed_quality_blocks_invalid_ask(self):
        feed = copy.deepcopy(self._feed())
        feed["ticks"][0]["ask"] = -1.0

        report = self._status(feed)

        self.assertEqual(report["status"], "INVALID")
        self.assertIs(report["all_ticks_valid"], False)
        self.assertEqual(_gate(report, "EURUSD", "ask_positive")["status"], "FAIL")

    def test_mt5_feed_quality_blocks_ask_less_or_equal_bid(self):
        feed = copy.deepcopy(self._feed())
        feed["ticks"][0]["ask"] = feed["ticks"][0]["bid"]

        report = self._status(feed)

        self.assertEqual(report["status"], "INVALID")
        self.assertIs(report["all_ticks_valid"], False)
        self.assertEqual(_gate(report, "EURUSD", "ask_greater_than_bid")["status"], "FAIL")

    def test_smoke_includes_mt5_feed_quality(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )
        names = {str(module["name"]) for module in report["modules"]}

        self.assertIn("mt5-feed-quality", names)
        self.assertEqual(report["status"], "PASS")

    def test_smoke_modules_count_19(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

        self.assertEqual(report["modules_count"], 19)


def _gate_symbols(report: dict[str, object]) -> set[str]:
    return {str(gate["symbol"]) for gate in report["gates"]}


def _gate(report: dict[str, object], symbol: str, name: str) -> dict[str, object]:
    for gate in report["gates"]:
        if gate["symbol"] == symbol and gate["gate_name"] == name:
            return gate
    raise AssertionError(f"missing gate {symbol}:{name}")


if __name__ == "__main__":
    unittest.main()

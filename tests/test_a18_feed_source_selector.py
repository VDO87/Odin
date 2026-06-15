import tempfile
import unittest
from pathlib import Path

from odin.core.smoke import run_runtime_smoke
from odin.data.feed_source_selector import feed_source_status


class A18FeedSourceSelectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _status(self):
        return feed_source_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_feed_source_selector_returns_ok(self):
        self.assertEqual(self._status()["status"], "OK")

    def test_feed_source_selector_mode_mock_only(self):
        self.assertEqual(self._status()["selector_mode"], "MOCK_ONLY")

    def test_feed_source_selected_mt5_feed_mock(self):
        self.assertEqual(self._status()["selected_source"], "mt5_feed_mock")

    def test_feed_source_fallback_market_data_mock(self):
        self.assertEqual(self._status()["fallback_source"], "market_data_mock")

    def test_feed_source_reads_mt5_feed_quality_status(self):
        self.assertEqual(self._status()["mt5_feed_quality_status"], "OK")

    def test_feed_source_mt5_feed_available_true(self):
        self.assertIs(self._status()["mt5_feed_available"], True)

    def test_feed_source_market_data_available_true(self):
        self.assertIs(self._status()["market_data_available"], True)

    def test_feed_source_safe_to_use_for_decision_false(self):
        self.assertIs(self._status()["safe_to_use_for_decision"], False)

    def test_feed_source_execution_allowed_false(self):
        self.assertIs(self._status()["execution_allowed"], False)

    def test_feed_source_safe_to_trade_false(self):
        self.assertIs(self._status()["safe_to_trade"], False)

    def test_feed_source_real_trading_false(self):
        self.assertIs(self._status()["real_trading"], False)

    def test_feed_source_includes_required_blockers(self):
        blockers = set(self._status()["blockers"])

        self.assertIn("decision_use_blocked", blockers)
        self.assertIn("execution_disabled", blockers)
        self.assertIn("real_trading_disabled", blockers)

    def test_smoke_includes_feed_source(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )
        names = {str(module["name"]) for module in report["modules"]}

        self.assertIn("feed-source", names)
        self.assertEqual(report["status"], "PASS")

    def test_smoke_modules_count_16(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

        self.assertEqual(report["modules_count"], 16)


if __name__ == "__main__":
    unittest.main()

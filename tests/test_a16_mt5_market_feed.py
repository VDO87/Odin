import tempfile
import unittest
from pathlib import Path

from odin.adapters.mt5.market_feed import mt5_market_feed_status
from odin.core.smoke import run_runtime_smoke


class A16MT5MarketFeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _status(self):
        return mt5_market_feed_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_mt5_market_feed_returns_ok(self):
        self.assertEqual(self._status()["status"], "OK")

    def test_mt5_market_feed_mode_mock_only(self):
        self.assertEqual(self._status()["feed_mode"], "MOCK_ONLY")

    def test_mt5_market_feed_provider_mock(self):
        self.assertEqual(self._status()["provider"], "mt5_mock")

    def test_mt5_market_feed_source_mock(self):
        self.assertEqual(self._status()["source"], "mt5_mock")

    def test_mt5_market_feed_connected_false(self):
        self.assertIs(self._status()["connected"], False)

    def test_mt5_market_feed_real_mt5_imported_false(self):
        self.assertIs(self._status()["real_mt5_imported"], False)

    def test_mt5_market_feed_symbols_count_3(self):
        self.assertEqual(self._status()["symbols_count"], 3)

    def test_mt5_market_feed_primary_symbol_eurusd(self):
        self.assertEqual(self._status()["primary_symbol"], "EURUSD")

    def test_eurusd_tick_values(self):
        tick = _tick(self._status(), "EURUSD")

        self.assertEqual(tick["bid"], 1.08500)
        self.assertEqual(tick["ask"], 1.08508)
        self.assertEqual(tick["spread"], 0.00008)

    def test_usdjpy_tick_values(self):
        tick = _tick(self._status(), "USDJPY")

        self.assertEqual(tick["bid"], 157.250)
        self.assertEqual(tick["ask"], 157.262)
        self.assertEqual(tick["spread"], 0.012)

    def test_gbpusd_tick_values(self):
        tick = _tick(self._status(), "GBPUSD")

        self.assertEqual(tick["bid"], 1.27400)
        self.assertEqual(tick["ask"], 1.27410)
        self.assertEqual(tick["spread"], 0.00010)

    def test_fire_assets_not_in_mt5_feed(self):
        symbols = {str(tick["symbol"]) for tick in self._status()["ticks"]}

        self.assertNotIn("VWCE", symbols)
        self.assertNotIn("IWDA", symbols)
        self.assertNotIn("EMIM", symbols)
        self.assertNotIn("CSPX", symbols)
        self.assertNotIn("AGGH", symbols)
        self.assertNotIn("XEON", symbols)

    def test_mt5_market_feed_execution_allowed_false(self):
        self.assertIs(self._status()["execution_allowed"], False)

    def test_mt5_market_feed_safe_to_trade_false(self):
        self.assertIs(self._status()["safe_to_trade"], False)

    def test_mt5_market_feed_real_trading_false(self):
        self.assertIs(self._status()["real_trading"], False)

    def test_smoke_includes_mt5_feed(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )
        names = {str(module["name"]) for module in report["modules"]}

        self.assertIn("mt5-feed", names)
        self.assertEqual(report["status"], "PASS")

    def test_smoke_modules_count_14(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

        self.assertEqual(report["modules_count"], 14)


def _tick(report: dict[str, object], symbol: str) -> dict[str, object]:
    for tick in report["ticks"]:
        if tick["symbol"] == symbol:
            return tick
    raise AssertionError(f"missing tick {symbol}")


if __name__ == "__main__":
    unittest.main()

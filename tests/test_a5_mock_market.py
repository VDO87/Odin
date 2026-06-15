import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.adapters.market_data.mock_market import MockMarketData, market_status
from odin.dashboard.routes import DashboardRoutes


class A5MockMarketTests(unittest.TestCase):
    def _market(self) -> MockMarketData:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        return MockMarketData(
            log_path=str(root / "logs" / "events.jsonl"),
            sqlite_path=str(root / "runtime" / "odin.sqlite"),
        )

    def tearDown(self):
        tmp = getattr(self, "tmp", None)
        if tmp is not None:
            tmp.cleanup()

    def test_market_status_returns_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = market_status(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["component"], "market_data")

    def test_market_status_is_mock_source(self):
        status = self._market().status()

        self.assertEqual(status["source"], "mock")

    def test_market_status_is_read_only(self):
        status = self._market().status()

        self.assertIs(status["read_only"], True)

    def test_market_status_execution_allowed_false(self):
        status = self._market().status()

        self.assertIs(status["execution_allowed"], False)

    def test_symbols_count_matches_total_watchlist(self):
        status = self._market().status()

        self.assertEqual(status["symbols_count"], len(status["watchlist"]))
        self.assertEqual(status["symbols_count"], 9)

    def test_forex_symbols_count_is_3(self):
        status = self._market().status()

        self.assertEqual(status["forex_symbols_count"], 3)

    def test_fire_symbols_count_is_6(self):
        status = self._market().status()

        self.assertEqual(status["fire_symbols_count"], 6)

    def test_market_status_keeps_safe_to_trade_false(self):
        status = self._market().status()

        self.assertIs(status["safe_to_trade"], False)

    def test_market_status_keeps_real_trading_false(self):
        status = self._market().status()

        self.assertIs(status["real_trading"], False)

    def test_mock_snapshot_eurusd_is_deterministic(self):
        snapshot = self._market().snapshot("EURUSD").to_dict()

        self.assertEqual(snapshot["symbol"], "EURUSD")
        self.assertEqual(snapshot["bid"], 1.08500)
        self.assertEqual(snapshot["ask"], 1.08508)
        self.assertEqual(snapshot["spread"], 0.00008)
        self.assertEqual(snapshot["source"], "mock")
        self.assertEqual(snapshot["quality_status"], "OK")

    def test_mock_candles_are_deterministic(self):
        candles = self._market().candles("EURUSD", "M15")

        self.assertEqual(len(candles), 5)
        self.assertEqual(candles[0]["open"], 1.08420)
        self.assertEqual(candles[-1]["close"], 1.08500)

    def test_cli_market_status_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "market-status"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        status = json.loads(completed.stdout)
        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["source"], "mock")
        self.assertEqual(status["symbols_count"], 9)
        self.assertEqual(status["forex_symbols_count"], 3)
        self.assertEqual(status["fire_symbols_count"], 6)
        self.assertIs(status["execution_allowed"], False)

    def test_dashboard_market_status_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/market/status")

        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["component"], "market_data")
        self.assertEqual(payload["symbols_count"], 9)
        self.assertEqual(payload["forex_symbols_count"], 3)
        self.assertEqual(payload["fire_symbols_count"], 6)
        self.assertIs(payload["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()

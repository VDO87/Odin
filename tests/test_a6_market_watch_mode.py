import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.core.market_watch import run_market_watch
from odin.dashboard.routes import DashboardRoutes


class A6MarketWatchModeTests(unittest.TestCase):
    def _watch(self) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            return run_market_watch(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

    def test_market_watch_returns_ok(self):
        status = self._watch()

        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["component"], "market_watch")

    def test_market_watch_mode_is_market_watch(self):
        status = self._watch()

        self.assertEqual(status["mode"], "MARKET_WATCH")

    def test_market_watch_source_is_mock(self):
        status = self._watch()

        self.assertEqual(status["source"], "mock")

    def test_market_watch_read_only_true(self):
        status = self._watch()

        self.assertIs(status["read_only"], True)

    def test_market_watch_safe_to_trade_false(self):
        status = self._watch()

        self.assertIs(status["safe_to_trade"], False)

    def test_market_watch_real_trading_false(self):
        status = self._watch()

        self.assertIs(status["real_trading"], False)

    def test_market_watch_execution_allowed_false(self):
        status = self._watch()

        self.assertIs(status["execution_allowed"], False)

    def test_market_watch_quality_status_ok(self):
        status = self._watch()

        self.assertEqual(status["quality_status"], "OK")

    def test_market_watch_decision_generated_false(self):
        status = self._watch()

        self.assertIs(status["decision_generated"], False)

    def test_market_watch_trade_proposal_generated_false(self):
        status = self._watch()

        self.assertIs(status["trade_proposal_generated"], False)

    def test_cli_market_watch_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "market-watch"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        status = json.loads(completed.stdout)
        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["mode"], "MARKET_WATCH")
        self.assertIs(status["execution_allowed"], False)
        self.assertIs(status["trade_proposal_generated"], False)

    def test_dashboard_market_watch_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/market/watch")

        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["mode"], "MARKET_WATCH")
        self.assertIs(payload["execution_allowed"], False)
        self.assertIs(payload["trade_proposal_generated"], False)


if __name__ == "__main__":
    unittest.main()


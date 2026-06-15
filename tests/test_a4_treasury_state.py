import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes
from odin.treasury.engine import compute_treasury_state, treasury_status


class A4TreasuryStateTests(unittest.TestCase):
    def test_treasury_status_returns_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status = treasury_status(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["component"], "treasury")

    def test_treasury_is_read_only(self):
        status = compute_treasury_state()

        self.assertIs(status["read_only"], True)

    def test_safe_to_transfer_false_by_default(self):
        status = compute_treasury_state()

        self.assertIs(status["safe_to_transfer"], False)

    def test_unrealized_profit_does_not_count_as_withdrawable(self):
        status = compute_treasury_state(unrealized_profit_eur=1000.0)

        self.assertEqual(status["withdrawable_surplus_eur"], 0.0)
        self.assertEqual(status["tax_reserve_eur"], 0.0)
        self.assertIs(status["safe_to_transfer"], False)

    def test_realized_profit_calculates_tax_reserve_30_percent(self):
        status = compute_treasury_state(realized_profit_eur=100.0)

        self.assertEqual(status["tax_reserve_eur"], 30.0)
        self.assertEqual(status["withdrawable_surplus_eur"], 70.0)
        self.assertIs(status["safe_to_transfer"], False)

    def test_cli_treasury_status_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "treasury-status"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        status = json.loads(completed.stdout)
        self.assertEqual(status["status"], "OK")
        self.assertEqual(status["jurisdiction"], "PT")
        self.assertIs(status["safe_to_transfer"], False)

    def test_dashboard_treasury_status_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/treasury/status")

        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["component"], "treasury")
        self.assertIs(payload["safe_to_transfer"], False)


if __name__ == "__main__":
    unittest.main()


import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


class A12SmokeCliDashboardTests(unittest.TestCase):
    def test_cli_smoke_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [sys.executable, "-m", "odin.cli", "smoke"],
                cwd=tmp,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["component"], "runtime_smoke")
        self.assertIs(report["all_modules_ok"], True)
        self.assertIs(report["execution_allowed"], False)

    def test_dashboard_runtime_smoke_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/runtime/smoke")

        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["component"], "runtime_smoke")
        self.assertEqual(payload["smoke_mode"], "LOCAL_SAFE_SMOKE")


if __name__ == "__main__":
    unittest.main()

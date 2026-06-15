import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


class A20ObservationFrameQualityCliDashboardTests(unittest.TestCase):
    def test_cli_observation_frame_quality_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "observation-frame-quality"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["component"], "observation_frame_quality")
        self.assertEqual(result["quality_mode"], "OBSERVATION_FRAME_GATES")
        self.assertEqual(result["selected_source"], "mt5_feed_mock")
        self.assertIs(result["execution_allowed"], False)

    def test_dashboard_observation_frame_quality_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/observation/frame/quality")

        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["component"], "observation_frame_quality")
        self.assertEqual(payload["primary_symbol"], "EURUSD")
        self.assertIs(payload["safe_to_trade"], False)


if __name__ == "__main__":
    unittest.main()

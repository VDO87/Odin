import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


class A11ShadowProposalCliDashboardTests(unittest.TestCase):
    def test_cli_shadow_proposal_returns_json(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd() / "src")
        completed = subprocess.run(
            [sys.executable, "-m", "odin.cli", "shadow-proposal"],
            cwd=Path.cwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        proposal = json.loads(completed.stdout)
        self.assertEqual(proposal["status"], "OK")
        self.assertEqual(proposal["component"], "shadow_proposal")
        self.assertEqual(proposal["shadow_proposal_status"], "BLOCKED")
        self.assertIs(proposal["shadow_only"], True)

    def test_dashboard_shadow_proposal_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            code, payload = routes.serve("/shadow/proposal")

        self.assertEqual(code, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["component"], "shadow_proposal")
        self.assertEqual(payload["shadow_mode"], "SHADOW_SKELETON")
        self.assertIs(payload["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()

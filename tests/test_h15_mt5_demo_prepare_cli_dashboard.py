import unittest
from unittest.mock import patch

from odin.cli import main
from odin.dashboard.routes import DashboardRoutes


class Mt5DemoPrepareCliDashboardTests(unittest.TestCase):
    def test_cli_preparation_is_local_and_execution_blocked(self):
        result = {"status": "READY_FOR_REVIEW", "execution_allowed": False, "terminal_connection_attempted": False}
        with patch("odin.cli.prepare_demo_session", return_value=result), patch("builtins.print"):
            code = main(["mt5-demo-prepare", "--account-mode", "demo"])
        self.assertEqual(code, 0)

    def test_dashboard_reads_reconciled_state_only(self):
        with patch("odin.dashboard.routes.reconcile_demo_session", return_value={"status": "READY_FOR_REVIEW", "execution_allowed": False, "terminal_connection_attempted": False}) as reconcile:
            status, result = DashboardRoutes().serve("/mt5/demo/session")
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertFalse(result["execution_allowed"])
        reconcile.assert_called_once()

    def test_dashboard_exposes_sanitized_demo_observation(self):
        status, result = DashboardRoutes().serve("/mt5/demo/observation")

        self.assertEqual(status, 200)
        self.assertFalse(result["execution_allowed"])
        self.assertNotIn("password", result)


if __name__ == "__main__":
    unittest.main()

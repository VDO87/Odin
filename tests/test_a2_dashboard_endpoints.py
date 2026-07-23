import tempfile
import unittest
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


class DashboardRoutesCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.routes = DashboardRoutes(
            log_path=str(root / "logs" / "events.jsonl"),
            sqlite_path=str(root / "runtime" / "odin.sqlite"),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def get_payload(self, path: str) -> dict[str, object]:
        status, payload = self.routes.serve(path)
        self.assertEqual(status, 200)
        return payload


class A2DashboardEndpointTests(DashboardRoutesCase):
    def test_health_endpoint_returns_ok(self):
        payload = self.get_payload("/health")

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["component"], "dashboard")
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)

    def test_state_endpoint_returns_off_safe(self):
        payload = self.get_payload("/state")

        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["mode"], "OFF_SAFE")
        self.assertIs(payload["safe_to_trade"], False)

    def test_state_endpoint_real_trading_false(self):
        payload = self.get_payload("/state")

        self.assertIs(payload["real_trading"], False)
        self.assertIs(payload["mt5_order_send_allowed"], False)
        self.assertIs(payload["xtb_automation_allowed"], False)

    def test_risk_status_ready_blocking(self):
        payload = self.get_payload("/risk/status")

        self.assertEqual(payload["risk_state"], "READY_BLOCKING")
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)
        self.assertEqual(
            payload["reason"],
            "A2 dashboard is read-only; risk engine remains blocking.",
        )

    def test_hermes_status_read_only(self):
        payload = self.get_payload("/hermes/status")

        self.assertEqual(payload["hermes_mode"], "READ_ONLY")
        self.assertIs(payload["can_write_config"], False)
        self.assertIs(payload["can_change_risk"], False)
        self.assertIs(payload["can_send_orders"], False)
        self.assertIs(payload["can_unlock_trading"], False)

    def test_logs_tail_handles_missing_file(self):
        payload = self.get_payload("/logs/tail")

        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["lines"], [])
        self.assertEqual(payload["reason"], "log file not found yet")

    def test_operations_events_endpoint_is_read_only(self):
        payload = self.get_payload("/operations/events")

        self.assertEqual(payload["component"], "operations_events")
        self.assertIs(payload["read_only"], True)
        self.assertEqual(payload["alerts_count"], 0)
        self.assertEqual(payload["alerts"], [])

    def test_cockpit_shell_is_local_and_read_only(self):
        page = self.routes.cockpit_html()

        self.assertIn("Provider policy", page)
        self.assertIn("Cloud fallback", page)
        self.assertIn("Config writes", page)
        self.assertIn("CPU load 1m", page)
        self.assertIn("Memory free", page)
        self.assertIn("Disk free", page)
        self.assertIn("GPU probe", page)
        self.assertIn("ODIN Cockpit", page)
        self.assertIn("/operations/overview", page)
        self.assertIn("/operations/events", page)
        self.assertNotIn("order_send", page)
        self.assertNotIn("POST", page)


if __name__ == "__main__":
    unittest.main()

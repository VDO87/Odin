import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_route_audit_reuses_initialized_sqlite_store(self):
        with patch.object(self.routes.store, "initialize") as initialize:
            self.get_payload("/health")

        initialize.assert_not_called()

    def test_operations_overview_reads_persistent_state_without_rebuilding_pipelines(self):
        autonomous = {
            "status": "OK",
            "supervisor": {
                "state": "WAITING_MARKET",
                "reason_codes": ["market_closed"],
                "updated_at_utc": "2026-08-29T22:00:00Z",
                "observed": {
                    "account_mode": "DEMO",
                    "broker": "OANDA TMS Brokers S.A.",
                    "terminal_connected": True,
                    "positions_count": 0,
                    "kill_switch_engaged": False,
                    "resources": {
                        "snapshot": {"hermes_running": True, "ollama_running": True},
                        "warning_codes": [],
                    },
                },
            },
            "heartbeat": {"fresh": True},
            "market": {"market_open": False, "data_freshness": "STALE"},
            "risk": {"status": "BLOCK"},
            "decision": None,
            "execution": {
                "status": "NO_ORDER",
                "reconciliation_status": "RECONCILED",
                "broker_submission_called": False,
            },
        }
        with patch(
            "odin.dashboard.routes.autonomous_demo_dashboard_state",
            return_value=autonomous,
        ) as read_state:
            payload = self.get_payload("/operations/overview")

        self.assertEqual(payload["source"], "persistent_autonomous_demo_state")
        self.assertEqual(payload["observation"]["market_status"], "WAITING_MARKET")
        self.assertEqual(
            payload["supervised_demo"]["mt5"]["status"],
            "CONNECTED_DEMO_READ_ONLY",
        )
        self.assertIs(payload["safety"]["execution_allowed"], False)
        read_state.assert_called_once()
        events = self.routes.logs_tail(limit=20)["lines"]
        event_names = [event["event"] for event in events]
        self.assertEqual(
            event_names,
            ["dashboard.request.received", "dashboard.state.served"],
        )

    def test_cockpit_shell_is_local_and_read_only(self):
        page = self.routes.cockpit_html()

        self.assertIn("ODIN Cockpit", page)
        self.assertIn("SHADOW INTELLIGENCE", page)
        self.assertIn("MT5 DEMO", page)
        self.assertIn("Hermes", page)
        self.assertNotIn("/operations/overview", page)
        self.assertIn("Live operational summary", page)
        self.assertIn("/operations/events", page)
        self.assertIn("/data/history/canonical", page)
        self.assertIn("/mt5/demo/audit", page)
        self.assertIn("/hermes/summary", page)
        self.assertNotIn("order_send", page)
        self.assertNotIn("POST", page)


if __name__ == "__main__":
    unittest.main()

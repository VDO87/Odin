import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odin.dashboard.routes import DashboardRoutes
from odin.trading.replay_config import save_replay_config


class ReplayConfigDashboardTests(unittest.TestCase):
    def test_route_persists_only_safe_replay_preferences(self):
        value = {"watchlist": ["EURUSD"], "risk_limits": {"daily_loss_limit": 90, "per_trade_risk_limit": 20, "max_position_lots": 0.03}}
        with tempfile.TemporaryDirectory() as tmp, patch("odin.dashboard.routes.save_replay_config", side_effect=lambda item: save_replay_config(item, str(Path(tmp) / "config.json"))):
            status, result = DashboardRoutes(log_path=str(Path(tmp) / "events.jsonl"), sqlite_path=str(Path(tmp) / "state.sqlite")).configure_replay(value)

        self.assertEqual(status, 200)
        self.assertEqual(result["configuration_status"], "SAVED")
        self.assertFalse(result["execution_allowed"])

    def test_tradedesk_has_replay_only_preferences_and_cockpit_stays_read_only(self):
        routes = DashboardRoutes()
        self.assertIn("/trading/replay/config", routes.tradedesk_html())
        self.assertIn("Replay preferences", routes.tradedesk_html())
        self.assertNotIn("POST", routes.cockpit_html())


if __name__ == "__main__":
    unittest.main()

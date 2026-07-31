import unittest

from odin.dashboard.routes import DashboardRoutes
from odin.trading.replay import replay_trading_state


class TradeDeskReplayTests(unittest.TestCase):
    def test_replay_account_has_visual_trading_information_but_no_execution(self):
        result = replay_trading_state()

        self.assertEqual(result["mode"], "DEMO_REPLAY")
        self.assertGreater(float(result["account"]["balance"]), 0)
        self.assertTrue(result["market"]["candles"])
        self.assertTrue(result["positions"])
        self.assertTrue(result["orders"])
        self.assertTrue(result["decision_journal"])
        self.assertIn("risk", result["decision_journal"][0])
        self.assertEqual(result["metrics"]["wins"], 1)
        self.assertEqual(result["metrics"]["losses"], 1)
        self.assertLess(float(result["metrics"]["net_profit"]), float(result["metrics"]["gross_profit"]))
        self.assertIn(result["public_data"]["status"], {"OK", "BLOCKED", "WARNING"})
        self.assertIs(result["execution_allowed"], False)

    def test_dashboard_exposes_replay_endpoint_and_separates_cockpit(self):
        routes = DashboardRoutes()
        status, payload = routes.serve("/trading/replay")

        self.assertEqual(status, 200)
        self.assertEqual(payload["component"], "trading_replay")
        self.assertIn("ODIN TradeDesk", routes.tradedesk_html())
        self.assertIn("Technical cockpit", routes.tradedesk_html())
        self.assertIn("MT5 DEMO open positions", routes.tradedesk_html())
        self.assertIn("Current terminal observation", routes.tradedesk_html())
        self.assertIn("Hermes local diagnostic", routes.tradedesk_html())
        self.assertIn("ODIN Cockpit", routes.cockpit_html())
        self.assertIs(payload["real_trading"], False)


if __name__ == "__main__":
    unittest.main()

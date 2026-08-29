import tempfile
import unittest
from pathlib import Path

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

    def test_dashboard_exposes_replay_endpoint_and_separates_human_and_technical_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            status, payload = routes.serve("/trading/replay")

        self.assertEqual(status, 200)
        self.assertEqual(payload["component"], "trading_replay")
        self.assertIn("ODIN TradeDesk", routes.tradedesk_html())
        self.assertIn("Visão Geral", routes.tradedesk_html())
        self.assertIn("Shadow / Aprendizagem", routes.tradedesk_html())
        self.assertIn("Performance", routes.tradedesk_html())
        self.assertIn("Equity e P/L · DEMO", routes.tradedesk_html())
        self.assertIn("Curva financeira reconciliada", routes.tradedesk_html())
        self.assertIn("equity_series", routes.tradedesk_html())
        self.assertIn("Replay fallback", routes.tradedesk_html())
        self.assertIn("setAttribute('d',line)", routes.tradedesk_html())
        self.assertIn("setAttribute('d',area)", routes.tradedesk_html())
        self.assertNotIn("line.replaceAll", routes.tradedesk_html())
        self.assertIn("P/L total · DEMO", routes.tradedesk_html())
        self.assertIn("Gate determinístico", routes.tradedesk_html())
        self.assertIn("Ciclo DEMO reconciliado", routes.tradedesk_html())
        self.assertIn("Spread limit", routes.tradedesk_html())
        self.assertIn("Timezone profile", routes.tradedesk_html())
        self.assertIn("maskTicket", routes.tradedesk_html())
        self.assertIn("OPEN REPORTS", routes.tradedesk_html())
        self.assertIn("supervisor-grid", routes.tradedesk_html())
        self.assertIn("Uptime", routes.tradedesk_html())
        self.assertIn("Próximo check", routes.tradedesk_html())
        self.assertIn("Último repair", routes.tradedesk_html())
        self.assertIn("successful_fix", routes.tradedesk_html())
        self.assertIn('href=\"/cockpit\"', routes.tradedesk_html())
        self.assertIn("MT5 DEMO · read-only", routes.tradedesk_html())
        self.assertIn("EXECUTION BLOCKED", routes.tradedesk_html())
        self.assertIn("Detalhes técnicos", routes.tradedesk_html())
        self.assertIn("Decisão live ODIN", routes.tradedesk_html())
        self.assertIn("display_source:'RUNTIME_STATE'", routes.tradedesk_html())
        self.assertIn("shadow_reference:shadowDecision", routes.tradedesk_html())
        self.assertIn(
            "q('shadow-freshness').textContent=shadowDecision.freshness",
            routes.tradedesk_html(),
        )
        self.assertNotIn(
            "observed.latest_decision?.decision_id?observed.latest_decision:shadowDecision",
            routes.tradedesk_html(),
        )
        self.assertIn("ODIN Cockpit", routes.cockpit_html())
        self.assertIs(payload["real_trading"], False)


if __name__ == "__main__":
    unittest.main()

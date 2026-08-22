import unittest
import tempfile
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


class A2DashboardSafeStateTests(unittest.TestCase):
    def test_dashboard_does_not_enable_real_trading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            routes = DashboardRoutes(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

            _, state = routes.serve("/state")
            _, health = routes.serve("/health")
            _, risk = routes.serve("/risk/status")

        self.assertIs(state["safe_to_trade"], False)
        self.assertIs(state["real_trading"], False)
        self.assertIs(health["safe_to_trade"], False)
        self.assertIs(health["real_trading"], False)
        self.assertIs(risk["safe_to_trade"], False)
        self.assertIs(risk["real_trading"], False)

    def test_dashboard_does_not_reference_mt5_order_send(self):
        text = _dashboard_text()

        self.assertNotIn("mt5.order", text)
        self.assertNotIn("order" + "_send", text)

    def test_dashboard_does_not_reference_xtb_automation(self):
        text = _dashboard_text()

        blocked_terms = [
            "xapi.xtb.com",
            "ws.xtb.com",
            "xtb api",
            "selenium",
            "playwright",
            "click",
            "mouse",
            "webdriver",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, text)


def _dashboard_text() -> str:
    parts = []
    for path in Path("src/odin/dashboard").rglob("*.py"):
        parts.append(path.read_text(encoding="utf-8").lower())
    return "\n".join(parts)


if __name__ == "__main__":
    unittest.main()

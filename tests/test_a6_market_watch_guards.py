import tempfile
import unittest
from pathlib import Path

from odin.core.bootstrap import validate_runtime
from odin.core.market_watch import run_market_watch


class A6MarketWatchGuardTests(unittest.TestCase):
    def test_market_watch_does_not_import_metatrader5(self):
        self.assertNotIn("metatrader5", _runtime_text())

    def test_market_watch_has_no_order_send(self):
        text = _runtime_text()

        self.assertNotIn("mt5.order" + "_send", text)
        self.assertNotIn("order" + "_send", text)

    def test_market_watch_has_no_xtb_api(self):
        text = _runtime_text()

        self.assertNotIn("xapi.xtb.com", text)
        self.assertNotIn("ws.xtb.com", text)

    def test_market_watch_has_no_buy_or_sell_signal(self):
        text = _runtime_text()

        self.assertNotIn("buy" + "_signal", text)
        self.assertNotIn("sell" + "_signal", text)

    def test_market_watch_has_no_trade_proposal(self):
        self.assertNotIn("trade" + "_proposal", _runtime_text())

    def test_market_watch_does_not_unlock_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_market_watch(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            state = validate_runtime(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

        self.assertIs(state["safe_to_trade"], False)
        self.assertIs(state["real_trading"], False)
        self.assertEqual(state["risk_state"], "READY_BLOCKING")

    def test_market_watch_has_no_extra_runtime_forbidden_terms(self):
        text = _runtime_text()
        blocked_terms = [
            "place" + "_order",
            "execute" + "_order",
            "approved" + "_by_risk",
            "send" + "_order",
            "selenium",
            "playwright",
            "click",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, text)


def _runtime_text() -> str:
    parts = []
    for path in Path("src/odin").rglob("*.py"):
        parts.append(path.read_text(encoding="utf-8").lower())
    return "\n".join(parts)


if __name__ == "__main__":
    unittest.main()


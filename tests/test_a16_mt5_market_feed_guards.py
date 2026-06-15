import tempfile
import unittest
from pathlib import Path

from odin.adapters.mt5.market_feed import mt5_market_feed_status
from odin.core.bootstrap import validate_runtime


class A16MT5MarketFeedGuardTests(unittest.TestCase):
    def test_mt5_feed_code_does_not_import_metatrader5(self):
        self.assertNotIn("metatrader5", _feed_runtime_text())

    def test_mt5_feed_code_has_no_mt5_dot(self):
        self.assertNotIn("mt5.", _feed_runtime_text())

    def test_mt5_feed_code_has_no_order_send(self):
        self.assertNotIn("order" + "_send", _feed_runtime_text())

    def test_mt5_feed_code_has_no_login(self):
        self.assertNotIn("login(", _feed_runtime_text())

    def test_mt5_feed_code_has_no_credentials(self):
        self.assertNotIn("cred" + "entials", _feed_runtime_text())

    def test_mt5_feed_code_has_no_buy_or_sell_signal(self):
        text = _feed_runtime_text()

        self.assertNotIn("buy" + "_signal", text)
        self.assertNotIn("sell" + "_signal", text)

    def test_mt5_feed_code_has_no_entry_sl_tp(self):
        text = _feed_runtime_text()

        self.assertNotIn("entry" + "_price", text)
        self.assertNotIn("stop" + "_loss", text)
        self.assertNotIn("take" + "_profit", text)

    def test_mt5_feed_code_has_no_position_size(self):
        self.assertNotIn("position" + "_size", _feed_runtime_text())

    def test_mt5_feed_code_does_not_unlock_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mt5_market_feed_status(
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

    def test_mt5_feed_code_has_no_extra_forbidden_terms(self):
        text = _feed_runtime_text()
        blocked_terms = [
            "account" + "_password",
            "server" + "_password",
            "send" + "_order",
            "place" + "_order",
            "execute" + "_order",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, text)


def _feed_runtime_text() -> str:
    roots = [
        Path("src/odin/adapters/mt5/market_feed.py"),
        Path("src/odin/contracts/mt5_market_feed.py"),
    ]
    return "\n".join(path.read_text(encoding="utf-8").lower() for path in roots)


if __name__ == "__main__":
    unittest.main()

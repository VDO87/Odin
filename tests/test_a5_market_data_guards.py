import tempfile
import unittest
from pathlib import Path

from odin.adapters.market_data.mock_market import market_status
from odin.core.bootstrap import validate_runtime


class A5MarketDataGuardTests(unittest.TestCase):
    def test_market_data_does_not_import_metatrader5(self):
        text = _runtime_text()

        self.assertNotIn("metatrader5", text)

    def test_market_data_has_no_order_send(self):
        text = _runtime_text()

        self.assertNotIn("mt5.order" + "_send", text)
        self.assertNotIn("order" + "_send", text)

    def test_market_data_has_no_xtb_api(self):
        text = _runtime_text()

        self.assertNotIn("xapi.xtb.com", text)
        self.assertNotIn("ws.xtb.com", text)

    def test_market_data_does_not_generate_trade_proposal(self):
        text = _runtime_text()

        self.assertNotIn("trade" + "_proposal", text)
        self.assertNotIn("buy" + "_signal", text)
        self.assertNotIn("sell" + "_signal", text)

    def test_market_data_does_not_unlock_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            market_status(
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

    def test_market_data_has_no_browser_automation_refs(self):
        text = _runtime_text()

        for term in ["selenium", "playwright", "click"]:
            self.assertNotIn(term, text)


def _runtime_text() -> str:
    roots = [Path("src/odin/adapters/market_data"), Path("src/odin/contracts/market.py")]
    parts = []
    for root in roots:
        if root.is_file():
            parts.append(root.read_text(encoding="utf-8").lower())
        else:
            parts.extend(path.read_text(encoding="utf-8").lower() for path in root.rglob("*.py"))
    return "\n".join(parts)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


class A7DataQualityGuardTests(unittest.TestCase):
    def test_data_quality_does_not_import_metatrader5(self):
        self.assertNotIn("metatrader5", _runtime_text())

    def test_data_quality_has_no_order_send(self):
        text = _runtime_text()

        self.assertNotIn("mt5.order" + "_send", text)
        self.assertNotIn("order" + "_send", text)

    def test_data_quality_has_no_xtb_api(self):
        text = _runtime_text()

        self.assertNotIn("xapi.xtb.com", text)
        self.assertNotIn("ws.xtb.com", text)

    def test_data_quality_has_no_buy_or_sell_signal(self):
        text = _runtime_text()

        self.assertNotIn("buy" + "_signal", text)
        self.assertNotIn("sell" + "_signal", text)

    def test_data_quality_has_no_trade_proposal(self):
        text = _runtime_text()

        self.assertNotIn("trade" + "_proposal", text)

    def test_data_quality_has_no_extra_forbidden_terms(self):
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
    roots = [Path("src/odin/data/quality.py"), Path("src/odin/contracts/quality.py")]
    return "\n".join(
        path.read_text(encoding="utf-8").lower() for path in roots if path.exists()
    )


if __name__ == "__main__":
    unittest.main()

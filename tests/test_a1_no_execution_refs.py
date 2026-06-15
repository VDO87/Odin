import unittest
from pathlib import Path


SRC_ROOT = Path("src/odin")


def _runtime_text() -> str:
    parts = []
    for path in SRC_ROOT.rglob("*.py"):
        parts.append(path.read_text(encoding="utf-8").lower())
    return "\n".join(parts)


class A1NoExecutionRefsTests(unittest.TestCase):
    def test_no_mt5_order_send_reference_in_src_runtime_code(self):
        text = _runtime_text()

        self.assertNotIn("mt5.order", text)
        self.assertNotIn("order" + "_send", text)

    def test_no_xtb_execution_or_click_automation_reference_in_src_runtime_code(self):
        text = _runtime_text()

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


if __name__ == "__main__":
    unittest.main()

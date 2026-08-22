import unittest
from pathlib import Path


SRC_ROOT = Path("src/odin")
DEMO_EXECUTION_ADAPTER = Path("src/odin/adapters/mt5/demo_execution_adapter.py")


def _runtime_text() -> str:
    parts = []
    for path in SRC_ROOT.rglob("*.py"):
        parts.append(path.read_text(encoding="utf-8").lower())
    return "\n".join(parts)


class A1NoExecutionRefsTests(unittest.TestCase):
    def test_mt5_order_send_is_absent_or_confined_to_single_demo_adapter(self):
        references = []
        for path in SRC_ROOT.rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            if "mt5.order" in text or "order" + "_send" in text:
                references.append(path)

        self.assertLessEqual(len(references), 1)
        self.assertTrue(all(path == DEMO_EXECUTION_ADAPTER for path in references))

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

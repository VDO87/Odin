import tempfile
import unittest
from pathlib import Path

from odin.core.bootstrap import validate_runtime
from odin.hermes.service import generate_hermes_summary


class A3HermesReadOnlyGuardTests(unittest.TestCase):
    def test_hermes_does_not_change_risk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = validate_runtime(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            summary = generate_hermes_summary(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            after = validate_runtime(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

        self.assertEqual(before["risk_state"], "READY_BLOCKING")
        self.assertEqual(summary["risk_state"], "READY_BLOCKING")
        self.assertEqual(after["risk_state"], "READY_BLOCKING")

    def test_hermes_does_not_unlock_trading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = generate_hermes_summary(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            after = validate_runtime(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

        self.assertIs(summary["safe_to_trade"], False)
        self.assertIs(summary["real_trading"], False)
        self.assertIs(after["safe_to_trade"], False)
        self.assertIs(after["real_trading"], False)

    def test_hermes_code_has_no_mt5_order_send(self):
        text = _runtime_text()

        self.assertNotIn("mt5.order", text)
        self.assertNotIn("order" + "_send", text)

    def test_hermes_code_has_no_xtb_automation(self):
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


def _runtime_text() -> str:
    parts = []
    for path in Path("src/odin/hermes").rglob("*.py"):
        parts.append(path.read_text(encoding="utf-8").lower())
    return "\n".join(parts)


if __name__ == "__main__":
    unittest.main()

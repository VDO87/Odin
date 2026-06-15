import tempfile
import unittest
from pathlib import Path

from odin.core.bootstrap import validate_runtime
from odin.treasury.engine import treasury_status


class A4TreasuryGuardTests(unittest.TestCase):
    def test_treasury_does_not_reference_banking_api(self):
        text = _runtime_text()

        blocked_terms = [
            "bank_transfer",
            "iban_send",
            "sepa_transfer",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, text)

    def test_treasury_does_not_reference_transfer_execution(self):
        text = _runtime_text()

        blocked_terms = [
            "execute_transfer",
            "withdraw_money",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, text)

    def test_treasury_does_not_unlock_trading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = validate_runtime(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            treasury_status(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            after = validate_runtime(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

        self.assertIs(before["safe_to_trade"], False)
        self.assertIs(after["safe_to_trade"], False)
        self.assertEqual(after["risk_state"], "READY_BLOCKING")

    def test_treasury_does_not_enable_real_trading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            treasury_status(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            state = validate_runtime(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

        self.assertIs(state["real_trading"], False)
        self.assertIs(state["safe_to_trade"], False)

    def test_treasury_code_has_no_market_or_ui_automation_refs(self):
        text = _runtime_text()

        blocked_terms = [
            "mt5.order",
            "order" + "_send",
            "xapi.xtb.com",
            "ws.xtb.com",
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


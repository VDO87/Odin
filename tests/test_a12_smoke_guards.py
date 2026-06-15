import tempfile
import unittest
from pathlib import Path

from odin.core.bootstrap import validate_runtime
from odin.core.smoke import run_runtime_smoke


class A12SmokeGuardTests(unittest.TestCase):
    def test_smoke_code_does_not_import_metatrader5(self):
        self.assertNotIn("metatrader5", _smoke_runtime_text())

    def test_smoke_code_has_no_order_send(self):
        text = _smoke_runtime_text()

        self.assertNotIn("mt5.order" + "_send", text)
        self.assertNotIn("order" + "_send", text)

    def test_smoke_code_has_no_xtb_api(self):
        text = _smoke_runtime_text()

        self.assertNotIn("xapi.xtb.com", text)
        self.assertNotIn("ws.xtb.com", text)

    def test_smoke_code_has_no_buy_or_sell_signal(self):
        text = _smoke_runtime_text()

        self.assertNotIn("buy" + "_signal", text)
        self.assertNotIn("sell" + "_signal", text)

    def test_smoke_code_has_no_entry_sl_tp(self):
        text = _smoke_runtime_text()

        self.assertNotIn("entry" + "_price", text)
        self.assertNotIn("stop" + "_loss", text)
        self.assertNotIn("take" + "_profit", text)

    def test_smoke_code_has_no_position_size(self):
        self.assertNotIn("position" + "_size", _smoke_runtime_text())

    def test_smoke_code_does_not_unlock_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_runtime_smoke(
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

    def test_smoke_code_does_not_approve_risk(self):
        text = _smoke_runtime_text()

        self.assertNotIn("approved" + "_by_risk", text)
        self.assertNotIn("risk_approved = true", text)

    def test_smoke_code_does_not_use_subprocess(self):
        text = _smoke_runtime_text()

        self.assertNotIn("sub" + "process", text)
        self.assertNotIn("os.system", text)
        self.assertNotIn("popen", text)

    def test_smoke_code_has_no_extra_forbidden_terms(self):
        text = _smoke_runtime_text()
        blocked_terms = [
            "place" + "_order",
            "execute" + "_order",
            "send" + "_order",
            "selenium",
            "playwright",
            "click",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, text)


def _smoke_runtime_text() -> str:
    roots = [
        Path("src/odin/core/smoke.py"),
        Path("src/odin/contracts/smoke.py"),
    ]
    return "\n".join(path.read_text(encoding="utf-8").lower() for path in roots)


if __name__ == "__main__":
    unittest.main()

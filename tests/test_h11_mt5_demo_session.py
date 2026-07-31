import json
import tempfile
import unittest
from pathlib import Path

from odin.adapters.mt5.demo_session import (
    detect_terminal_installation,
    prepare_demo_session,
    reconcile_demo_session,
)


class MT5DemoSessionTests(unittest.TestCase):
    def test_detection_only_does_not_connect(self):
        with tempfile.TemporaryDirectory() as tmp:
            terminal = Path(tmp) / "terminal.exe"
            terminal.write_bytes(b"placeholder")
            result = detect_terminal_installation(str(terminal))

        self.assertEqual(result["status"], "OK")
        self.assertIs(result["terminal_connection_attempted"], False)
        self.assertIs(result["execution_allowed"], False)

    def test_demo_state_is_redacted_persisted_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            terminal = root / "terminal.exe"
            terminal.write_bytes(b"placeholder")
            state = root / "state.json"
            first = prepare_demo_session(account_mode="demo", terminal_path=str(terminal), state_path=str(state), kill_switch_engaged=False)
            second = prepare_demo_session(account_mode="demo", terminal_path=str(terminal), state_path=str(state), kill_switch_engaged=False)
            saved = json.loads(state.read_text(encoding="utf-8"))

        self.assertEqual(first["status"], "READY_FOR_REVIEW")
        self.assertTrue(second["idempotent_reuse"])
        self.assertFalse(saved["access_material_present"])
        self.assertNotIn("password", json.dumps(saved).lower())
        self.assertIs(first["execution_allowed"], False)

    def test_kill_switch_and_real_mode_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            terminal = Path(tmp) / "terminal.exe"
            terminal.write_bytes(b"placeholder")
            stopped = prepare_demo_session(account_mode="demo", terminal_path=str(terminal), state_path=str(Path(tmp) / "stopped.json"), kill_switch_engaged=True)
            real = prepare_demo_session(account_mode="real", terminal_path=str(terminal), state_path=str(Path(tmp) / "real.json"), kill_switch_engaged=False)

        self.assertEqual(stopped["reason"], "kill_switch_engaged")
        self.assertEqual(real["reason"], "real_account_mode_rejected")
        self.assertIs(stopped["safe_to_trade"], False)

    def test_reconciliation_never_authorizes_login_or_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            terminal = root / "terminal.exe"
            terminal.write_bytes(b"placeholder")
            state = root / "state.json"
            prepare_demo_session(account_mode="demo", terminal_path=str(terminal), state_path=str(state), kill_switch_engaged=False)
            result = reconcile_demo_session(str(state))

        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertIs(result["terminal_connection_attempted"], False)
        self.assertIs(result["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()

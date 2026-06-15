import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from odin.core.bootstrap import validate_runtime


class A1ValidateSafeStateTests(unittest.TestCase):
    def _validate(self) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            return validate_runtime(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )

    def test_validate_returns_pass_in_off_safe(self):
        result = self._validate()

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mode"], "OFF_SAFE")

    def test_safe_to_trade_is_false_by_default(self):
        result = self._validate()

        self.assertIs(result["safe_to_trade"], False)

    def test_real_trading_is_false_by_default(self):
        result = self._validate()

        self.assertIs(result["real_trading"], False)

    def test_mt5_order_send_allowed_is_false_by_default(self):
        result = self._validate()

        self.assertIs(result["mt5_order_send_allowed"], False)

    def test_xtb_automation_allowed_is_false_by_default(self):
        result = self._validate()

        self.assertIs(result["xtb_automation_allowed"], False)

    def test_risk_engine_placeholder_is_ready_blocking(self):
        result = self._validate()

        self.assertEqual(result["risk_state"], "READY_BLOCKING")

    def test_hermes_is_read_only(self):
        result = self._validate()

        self.assertEqual(result["hermes_mode"], "READ_ONLY")

    def test_python_module_cli_validate_returns_safe_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path.cwd()
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root / "src")
            completed = subprocess.run(
                [sys.executable, "-m", "odin.cli", "validate"],
                cwd=tmp,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mode"], "OFF_SAFE")
        self.assertIs(result["safe_to_trade"], False)
        self.assertIs(result["real_trading"], False)


if __name__ == "__main__":
    unittest.main()

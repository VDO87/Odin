import tempfile
import unittest
from pathlib import Path

from odin.trading.replay_config import load_replay_config, save_replay_config, validate_replay_config


class ReplayConfigTests(unittest.TestCase):
    def test_valid_config_persists_and_stays_execution_blocked(self):
        value = {"watchlist": ["EURUSD", "GBPUSD"], "risk_limits": {"daily_loss_limit": 80, "per_trade_risk_limit": 20, "max_position_lots": 0.04}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "replay.json"
            saved = save_replay_config(value, str(path))
            loaded = load_replay_config(str(path))

        self.assertEqual(saved["configuration_status"], "SAVED")
        self.assertEqual(loaded["watchlist"], ["EURUSD", "GBPUSD"])
        self.assertFalse(loaded["execution_allowed"])
        self.assertFalse(loaded["safe_to_trade"])
        self.assertFalse(loaded["real_trading"])

    def test_unknown_fields_and_symbols_fail_closed(self):
        invalid = {"watchlist": ["XAUUSD"], "risk_limits": {"daily_loss_limit": 80, "per_trade_risk_limit": 20, "max_position_lots": 0.04}, "execution_allowed": True}
        result = validate_replay_config(invalid)

        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["execution_allowed"])

    def test_invalid_file_falls_back_to_blocked_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "replay.json"
            path.write_text("not json", encoding="utf-8")
            result = load_replay_config(str(path))

        self.assertEqual(result["configuration_status"], "INVALID_BLOCKED")
        self.assertFalse(result["execution_allowed"])


if __name__ == "__main__":
    unittest.main()

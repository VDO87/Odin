import json
import tempfile
import unittest
from pathlib import Path
from odin.adapters.mt5.demo_readonly_state import read_demo_readonly_state

class Mt5DemoTradeDeskTests(unittest.TestCase):
    def test_sanitized_demo_state_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "state.json"
            p.write_text(json.dumps({"status":"CONNECTED_DEMO_READ_ONLY","as_of":"x","account":{"currency":"EUR","balance":0,"equity":0,"margin":0,"free_margin":0,"password":"hidden"},"positions":[],"market":{"symbol":"EURUSD","status":"OK","bid":1.0,"ask":1.1,"as_of":"x","candles":[{"time":"x","open":1.0,"high":1.1,"low":0.9,"close":1.05,"secret":"hidden"}]},"terminal_connected":True}),encoding="utf-8")
            state = read_demo_readonly_state(str(p))
        self.assertEqual(state["status"],"CONNECTED_DEMO_READ_ONLY")
        self.assertNotIn("password",state["account"])
        self.assertNotIn("secret",state["market"]["candles"][0])
        self.assertEqual(state["market"]["symbol"], "EURUSD")
        self.assertFalse(state["execution_allowed"])

if __name__ == "__main__":
    unittest.main()

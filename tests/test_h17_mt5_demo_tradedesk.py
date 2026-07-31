import json
import tempfile
import unittest
from pathlib import Path
from odin.adapters.mt5.demo_readonly_state import read_demo_readonly_state

class Mt5DemoTradeDeskTests(unittest.TestCase):
    def test_sanitized_demo_state_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "state.json"
            p.write_text(json.dumps({"status":"CONNECTED_DEMO_READ_ONLY","as_of":"x","account":{"currency":"EUR","balance":0,"equity":0,"margin":0,"free_margin":0,"password":"hidden"},"positions":[],"terminal_connected":True}),encoding="utf-8")
            state = read_demo_readonly_state(str(p))
        self.assertEqual(state["status"],"CONNECTED_DEMO_READ_ONLY")
        self.assertNotIn("password",state["account"])
        self.assertFalse(state["execution_allowed"])

if __name__ == "__main__":
    unittest.main()

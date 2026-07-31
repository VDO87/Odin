import json
import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from odin.adapters.mt5.demo_readonly_state import read_demo_observation_audit, read_demo_readonly_state

class Mt5DemoTradeDeskTests(unittest.TestCase):
    @staticmethod
    def _signed_state(now: datetime) -> dict[str, object]:
        value: dict[str, object] = {"status":"CONNECTED_DEMO_READ_ONLY","as_of":now.isoformat(),"account":{"currency":"EUR","balance":0,"equity":0,"margin":0,"free_margin":0,"password":"hidden"},"positions":[],"market":{"symbol":"EURUSD","status":"OK","bid":1.0,"ask":1.1,"as_of":now.isoformat(),"candles":[{"time":"x","open":1.0,"high":1.1,"low":0.9,"close":1.05,"secret":"hidden"}]},"terminal_connected":True,"execution_allowed":False,"safe_to_trade":False,"real_trading":False}
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
        value["content_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return value

    def test_sanitized_demo_state_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "state.json"
            now = datetime.now(timezone.utc)
            p.write_text(json.dumps(self._signed_state(now)),encoding="utf-8")
            state = read_demo_readonly_state(str(p), now=now)
        self.assertEqual(state["status"],"CONNECTED_DEMO_READ_ONLY")
        self.assertNotIn("password",state["account"])
        self.assertNotIn("secret",state["market"]["candles"][0])
        self.assertEqual(state["market"]["symbol"], "EURUSD")
        self.assertTrue(state["fresh"])
        self.assertFalse(state["execution_allowed"])

    def test_stale_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "state.json"
            now = datetime.now(timezone.utc)
            p.write_text(json.dumps(self._signed_state(now - timedelta(minutes=16))),encoding="utf-8")
            state = read_demo_readonly_state(str(p), now=now)
        self.assertEqual(state["status"], "BLOCKED")
        self.assertEqual(state["reason"], "demo_readonly_state_stale")
        self.assertFalse(state["execution_allowed"])

    def test_changed_signed_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "state.json"
            value = self._signed_state(datetime.now(timezone.utc))
            value["account"]["equity"] = 999  # type: ignore[index]
            p.write_text(json.dumps(value), encoding="utf-8")
            state = read_demo_readonly_state(str(p))
        self.assertEqual(state["status"], "BLOCKED")
        self.assertEqual(state["reason"], "demo_readonly_state_integrity_failed")

    def test_audit_reader_sanitizes_bounded_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "audit.jsonl"
            p.write_text(json.dumps({"event":"mt5_demo_readonly_snapshot","as_of":"x","status":"CONNECTED_DEMO_READ_ONLY","positions_count":0,"content_hash":"hash","market":{"symbol":"EURUSD","candles":32,"password":"hidden"}})+"\nnot-json",encoding="utf-8")
            audit = read_demo_observation_audit(str(p))
        self.assertEqual(audit["status"], "OK")
        self.assertEqual(len(audit["events"]), 1)
        self.assertNotIn("password", audit["events"][0]["market"])
        self.assertFalse(audit["execution_allowed"])

if __name__ == "__main__":
    unittest.main()

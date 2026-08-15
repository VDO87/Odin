import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odin.contracts.events import OdinEvent
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


class SecretEventRedactionTests(unittest.TestCase):
    def test_mt5_env_values_and_sensitive_fields_never_reach_jsonl_or_sqlite(self):
        password = "demo-password-sentinel"
        login = "demo-login-sentinel"
        server = "demo-server-sentinel"
        payload = {
            "note": password,
            "nested": [login, {"server_hint": server, "api_token": "also-hidden"}],
            "safe": "kept",
        }
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "ODIN_MT5_PASSWORD": password,
            "ODIN_MT5_LOGIN": login,
            "ODIN_MT5_SERVER": server,
        }, clear=False):
            event = OdinEvent.create(run_id="redaction-test", component="odin.test", event="test", payload=payload)
            logger = JsonlLogger(Path(tmp) / "events.jsonl")
            logger.write(event)
            store = SQLiteStore(Path(tmp) / "events.sqlite")
            store.initialize()
            store.record_event(event)
            jsonl = (Path(tmp) / "events.jsonl").read_text(encoding="utf-8")
            with store.connect() as connection:
                sqlite = connection.execute("SELECT payload_json FROM events").fetchone()[0]

        for forbidden in (password, login, server, "also-hidden"):
            self.assertNotIn(forbidden, jsonl)
            self.assertNotIn(forbidden, sqlite)
        self.assertIn("kept", jsonl)
        self.assertIn("[REDACTED]", jsonl)


if __name__ == "__main__":
    unittest.main()

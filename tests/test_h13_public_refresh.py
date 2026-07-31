import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odin.data.public_refresh import refresh_ecb_public_data


class PublicRefreshTests(unittest.TestCase):
    def test_success_persists_metadata_to_jsonl_and_sqlite(self):
        observed = {
            "status": "OK", "source": "ecb_exr", "source_url": "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A",
            "content_hash": "abc", "content_length": 20, "retrieved_at": "2026-07-31T10:00:00+00:00",
            "safe_to_trade": False, "execution_allowed": False, "real_trading": False,
        }
        with tempfile.TemporaryDirectory() as tmp, patch("odin.data.public_refresh.fetch_ecb_exchange_rate", return_value=observed):
            root = Path(tmp)
            result = refresh_ecb_public_data(cache_root=str(root / "cache"), log_path=str(root / "events.jsonl"), sqlite_path=str(root / "state.sqlite"))
            events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
            sqlite_exists = (root / "state.sqlite").is_file()

        self.assertEqual(result["status"], "OK")
        self.assertTrue(result["audit_persisted"])
        self.assertEqual([event["event"] for event in events], ["public_data.refresh.requested", "public_data.refresh.completed"])
        self.assertNotIn("cache_path", events[-1]["payload"])
        self.assertTrue(sqlite_exists)

    def test_failure_is_persisted_and_remains_fail_closed(self):
        observed = {"status": "BLOCKED", "reason": "public_provider_fetch_failed", "events": ["public_data.failure"], "execution_allowed": False, "safe_to_trade": False, "real_trading": False}
        with tempfile.TemporaryDirectory() as tmp, patch("odin.data.public_refresh.fetch_ecb_exchange_rate", return_value=observed):
            root = Path(tmp)
            result = refresh_ecb_public_data(log_path=str(root / "events.jsonl"), sqlite_path=str(root / "state.sqlite"))
            events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["execution_allowed"])
        self.assertEqual(events[-1]["event"], "public_data.refresh.blocked")


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from odin.contracts.events import LOGGING_JSONL_READY, OdinEvent
from odin.logging.jsonl_logger import JsonlLogger


class A1JsonlLoggerTests(unittest.TestCase):
    def test_jsonl_logger_writes_valid_json_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logs" / "events.jsonl"
            logger = JsonlLogger(path)
            event = OdinEvent.create(
                run_id="test-run",
                component="odin.logging",
                event=LOGGING_JSONL_READY,
            )

            logger.write(event)

            lines = path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertTrue(record["timestamp"])
        self.assertEqual(record["run_id"], "test-run")
        self.assertTrue(record["corr_id"])
        self.assertEqual(record["component"], "odin.logging")
        self.assertEqual(record["event"], LOGGING_JSONL_READY)
        self.assertEqual(record["severity"], "INFO")
        self.assertEqual(record["mode"], "OFF_SAFE")
        self.assertIsNone(record["symbol"])
        self.assertIs(record["safe_to_trade"], False)
        self.assertEqual(record["reason"], "fail_closed")
        self.assertEqual(record["payload"], {})


if __name__ == "__main__":
    unittest.main()

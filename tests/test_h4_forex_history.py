import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from odin.data.forex_history import assess_history_quality, load_forex_history


CSV = """timestamp,open,high,low,close,volume,spread
2026-07-01T00:00:00+00:00,1.1,1.2,1.0,1.15,10,0.0001
2026-07-01T00:15:00+00:00,1.15,1.25,1.1,1.2,11,0.0001
"""


class ForexHistoryTests(unittest.TestCase):
    def _file(self, text: str) -> str:
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "EURUSD_M15.csv"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_valid_history_is_read_only_and_provenanced(self):
        report = load_forex_history(
            self._file(CSV), symbol="EURUSD", timeframe="M15", source="local_csv"
        )

        self.assertEqual(report["status"], "OK")
        self.assertEqual(report["candles_count"], 2)
        self.assertEqual(report["source"], "local_csv")
        self.assertIs(report["execution_allowed"], False)
        self.assertIs(report["safe_to_trade"], False)

    def test_invalid_schema_fails_closed(self):
        report = load_forex_history(
            self._file("timestamp,close\n2026-07-01T00:00:00+00:00,1.1\n"),
            symbol="EURUSD",
            timeframe="M15",
            source="local_csv",
        )

        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["reason"], "history_schema_invalid")
        self.assertIs(report["execution_allowed"], False)

    def test_duplicate_timestamp_fails_closed(self):
        report = load_forex_history(
            self._file(CSV + "2026-07-01T00:15:00+00:00,1.2,1.3,1.1,1.25,12,0.0001\n"),
            symbol="EURUSD",
            timeframe="M15",
            source="local_csv",
        )

        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["reason"], "history_timestamps_not_strictly_ascending")

    def test_quality_reports_fresh_history_without_gaps(self):
        history = load_forex_history(
            self._file(CSV), symbol="EURUSD", timeframe="M15", source="local_csv"
        )
        quality = assess_history_quality(
            history, now=datetime(2026, 7, 1, 0, 30, tzinfo=UTC)
        )

        self.assertEqual(quality["status"], "OK")
        self.assertIs(quality["fresh"], True)
        self.assertEqual(quality["gaps_count"], 0)
        self.assertIs(quality["execution_allowed"], False)

    def test_quality_warns_for_stale_history_and_gaps(self):
        history = load_forex_history(
            self._file(CSV), symbol="EURUSD", timeframe="M15", source="local_csv"
        )
        history["candles"][1]["timestamp"] = "2026-07-01T02:00:00+00:00"
        quality = assess_history_quality(
            history,
            now=datetime(2026, 7, 5, tzinfo=UTC),
            max_age=timedelta(days=1),
        )

        self.assertEqual(quality["status"], "WARNING")
        self.assertIs(quality["fresh"], False)
        self.assertEqual(quality["gaps_count"], 1)


if __name__ == "__main__":
    unittest.main()

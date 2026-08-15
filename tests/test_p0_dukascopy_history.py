import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError

from odin.data.dukascopy_history import (
    DUKASCOPY_EXPORT_URL,
    DUKASCOPY_TERMS_URL,
    DukascopyHistoryError,
    DukascopySourceRateLimited,
    _fetch_json,
    aggregate_m1_to_m15,
    decode_minute_payload,
    import_manual_dukascopy_eurusd_m1,
    source_rate_limited_status,
)


class DukascopyHistoryTests(unittest.TestCase):
    def test_decodes_vendor_delta_payload_and_aggregates_complete_utc_window(self):
        payload = {
            "timestamp": 0, "shift": 60000, "multiplier": 0.00001,
            "open": 1.10000, "high": 1.10000, "low": 1.10000, "close": 1.10000,
            "times": [0] + [1] * 14, "opens": [0] * 15, "highs": [2] * 15,
            "lows": [-2] * 15, "closes": [2] * 15, "volumes": [1] * 15,
        }
        m15 = aggregate_m1_to_m15(decode_minute_payload(payload))
        self.assertEqual(len(m15), 1)
        self.assertEqual(m15[0]["timestamp_ms"], 0)
        self.assertEqual(m15[0]["open"], 1.1)
        self.assertEqual(m15[0]["close"], 1.1003)
        self.assertEqual(m15[0]["volume"], 15.0)

    def test_rejects_incomplete_or_non_monotonic_m1_windows(self):
        incomplete = [{"timestamp_ms": index * 60000, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0} for index in range(14)]
        with self.assertRaisesRegex(DukascopyHistoryError, "incomplete"):
            aggregate_m1_to_m15(incomplete)
        unordered = [
            {"timestamp_ms": 60000, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
            {"timestamp_ms": 0, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0},
        ]
        with self.assertRaisesRegex(DukascopyHistoryError, "ordering"):
            aggregate_m1_to_m15(unordered)

    def test_accepts_an_explicit_vendor_market_closure_payload(self):
        payload = {"timestamp": 0, "shift": 60000, "multiplier": 0.00001, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0,
                   "times": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
        self.assertEqual(decode_minute_payload(payload), [])

    def test_429_is_bounded_and_reported_as_external_transient(self):
        attempts = []
        waits = []

        def limited(*_args, **_kwargs):
            attempts.append(1)
            raise HTTPError("https://vendor.invalid", 429, "limited", {"Retry-After": "120"}, None)

        with self.assertRaises(DukascopySourceRateLimited) as raised:
            _fetch_json("https://vendor.invalid", 1, opener=limited, sleeper=waits.append, jitter=lambda *_: 0)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(waits, [120.0, 120.0])
        self.assertEqual(source_rate_limited_status(raised.exception)["reason"], "SOURCE_RATE_LIMITED")

    def test_manual_official_m1_export_is_aggregated_and_persisted_only_after_validation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "EURUSD_M1_BID_UTC.csv"
            lines = ["UTC,Open,High,Low,Close,Volume"]
            for minute in range(30):
                timestamp = datetime(2025, 7, 1, 0, minute, tzinfo=UTC).isoformat()
                lines.append(f"{timestamp},1.10000,1.10020,1.09980,1.10010,1")
            raw.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = import_manual_dukascopy_eurusd_m1(
                csv_path=raw, acquired_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
                source_url=DUKASCOPY_EXPORT_URL, terms_url=DUKASCOPY_TERMS_URL, artifact_root=root,
            )
            self.assertEqual(result["status"], "VALIDATED")
            self.assertEqual(result["source_rows_m1"], 30)
            manifest = Path(result["manifest_path"]).read_text(encoding="utf-8")
            self.assertIn("manual_Dukascopy_Historical_Data_Export", manifest)
            self.assertIn(DUKASCOPY_EXPORT_URL, manifest)
            self.assertIn("M1_to_M15_UTC_complete_windows_v1", manifest)

    def test_manual_export_rejects_non_utc_file_before_artifact_creation(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "invalid.csv"
            raw.write_text("UTC,Open,High,Low,Close,Volume\n2025-07-01T00:00:00+01:00,1,1,1,1,1\n", encoding="utf-8")
            with self.assertRaisesRegex(DukascopyHistoryError, "manual_row_invalid"):
                import_manual_dukascopy_eurusd_m1(
                    csv_path=raw, acquired_at=datetime(2026, 8, 15, tzinfo=UTC),
                    source_url=DUKASCOPY_EXPORT_URL, terms_url=DUKASCOPY_TERMS_URL, artifact_root=root,
                )
            self.assertFalse((root / "artifacts" / "market-data").exists())

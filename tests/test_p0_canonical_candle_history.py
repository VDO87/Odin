import csv
import json
import tempfile
import unittest
from pathlib import Path

from odin.contracts.historical_candles import CANONICAL_CANDLE_COLUMNS, CANONICAL_CANDLE_SCHEMA_VERSION
from odin.data.canonical_candle_history import (
    canonical_candle_history_status,
    canonical_dataset_hash,
    import_canonical_candle_history,
)
from odin.dashboard.routes import DashboardRoutes


class CanonicalCandleHistoryTests(unittest.TestCase):
    def _rows(self):
        base = {
            "symbol": "EURUSD", "timeframe": "M15", "open": "1.1000", "high": "1.2000",
            "low": "1.0000", "close": "1.1500", "volume": "10", "source": "test-fixture",
            "source_version": "2026.08", "schema_version": CANONICAL_CANDLE_SCHEMA_VERSION,
            "provenance": "fixture://unit-test", "license": "test-only",
        }
        rows = [dict(base, timestamp_utc="2026-08-14T23:45:00Z"), dict(base, timestamp_utc="2026-08-15T00:00:00Z", volume="11")]
        digest = canonical_dataset_hash(rows)
        return [dict(row, hash=digest) for row in rows]

    def _csv(self, rows, *, headers=CANONICAL_CANDLE_COLUMNS):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        path = Path(root.name) / "candles.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return path, Path(root.name) / "odin-local"

    def test_valid_dataset_is_persisted_with_manifest(self):
        path, root = self._csv(self._rows())
        result = import_canonical_candle_history(path, symbol="EURUSD", timeframe="M15", artifact_root=root)
        self.assertEqual(result["status"], "VALIDATED")
        self.assertTrue(Path(result["artifact_path"]).is_file())
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["quality_status"], "VALIDATED")
        self.assertEqual(manifest["source"], "test-fixture")
        self.assertFalse(result["execution_allowed"])
        self.assertEqual(canonical_candle_history_status(artifact_root=root)["status"], "OK")

    def test_invalid_schema_never_creates_artifact(self):
        rows = self._rows()
        path, root = self._csv(rows, headers=CANONICAL_CANDLE_COLUMNS[:-1])
        result = import_canonical_candle_history(path, symbol="EURUSD", timeframe="M15", artifact_root=root)
        self.assertEqual(result["reason"], "canonical_schema_invalid")
        self.assertFalse((root / "artifacts").exists())

    def test_manifest_extras_cannot_override_canonical_provenance(self):
        path, root = self._csv(self._rows())
        result = import_canonical_candle_history(
            path, symbol="EURUSD", timeframe="M15", artifact_root=root,
            manifest_extras={"source": "replacement"},
        )
        self.assertEqual(result["reason"], "manifest_extras_override_canonical_field")
        self.assertFalse((root / "artifacts").exists())

    def test_rejects_non_utc_duplicate_gap_ohlc_and_non_finite_values(self):
        cases = [
            ("timestamp_utc", "2026-08-15T00:00:00+01:00", "canonical_timestamp_or_number_invalid"),
            ("timestamp_utc", "2026-08-14T23:45:00Z", "canonical_timestamps_not_strictly_ascending"),
            ("timestamp_utc", "2026-08-15T00:30:00Z", "canonical_gap_incompatible"),
            ("high", "nan", "canonical_non_finite_value"),
            ("low", "1.1600", "canonical_ohlcv_invalid"),
        ]
        for field, value, reason in cases:
            with self.subTest(field=field, value=value):
                rows = self._rows()
                rows[1][field] = value
                digest = canonical_dataset_hash([{key: row[key] for key in CANONICAL_CANDLE_COLUMNS if key != "hash"} for row in rows])
                for row in rows:
                    row["hash"] = digest
                path, root = self._csv(rows)
                result = import_canonical_candle_history(path, symbol="EURUSD", timeframe="M15", artifact_root=root)
                self.assertEqual(result["reason"], reason)
                self.assertFalse((root / "artifacts").exists())

    def test_dashboard_exposes_history_status_and_tradedesk_labels_it_as_evidence(self):
        routes = DashboardRoutes()
        status, payload = routes.serve("/data/history/canonical")
        self.assertEqual(status, 200)
        self.assertIn(payload["status"], {"OK", "BLOCKED"})
        page = routes.tradedesk_html()
        self.assertIn("/data/history/canonical", page)
        self.assertIn("historical_dataset", page)

    def test_rejects_missing_provenance_hash_and_identity_mismatch(self):
        for field, value, expected_symbol, reason in [
            ("provenance", "", "EURUSD", "canonical_required_value_missing"),
            ("hash", "0" * 64, "EURUSD", "dataset_hash_invalid"),
            ("symbol", "GBPUSD", "EURUSD", "canonical_symbol_or_timeframe_mismatch"),
        ]:
            with self.subTest(field=field):
                rows = self._rows()
                for row in rows:
                    row[field] = value
                if field not in {"hash", "provenance"}:
                    digest = canonical_dataset_hash([{key: row[key] for key in CANONICAL_CANDLE_COLUMNS if key != "hash"} for row in rows])
                    for row in rows:
                        row["hash"] = digest
                path, root = self._csv(rows)
                result = import_canonical_candle_history(path, symbol=expected_symbol, timeframe="M15", artifact_root=root)
                self.assertEqual(result["reason"], reason)


if __name__ == "__main__":
    unittest.main()

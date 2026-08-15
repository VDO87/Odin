import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from odin.data.mt5_oanda_history import Mt5OandaHistoryError, import_mt5_oanda_tms_m1


class Mt5OandaP0Tests(unittest.TestCase):
    def _rates(self, start, minutes, missing=()):
        rows = []
        for index in range(minutes):
            if index in missing:
                continue
            stamp = start + timedelta(minutes=index)
            price = 1.1 + index / 100000
            rows.append(
                {
                    "time": int(stamp.timestamp()),
                    "open": price,
                    "high": price + 0.0001,
                    "low": price - 0.0001,
                    "close": price + 0.00005,
                    "tick_volume": 10,
                    "spread": 2,
                    "real_volume": 0,
                }
            )
        return rows

    def test_no_tick_gap_is_retained_not_filled_and_manifested(self):
        start = datetime(2026, 7, 1, tzinfo=UTC)
        end = start + timedelta(minutes=60)
        # One absent minute makes its M15 window unavailable; the later gap is
        # explicitly attached to canonical continuity rather than repaired.
        rates = self._rates(start, 60, missing=(15,))
        ticks = {
            (
                int((start + timedelta(minutes=15)).timestamp() * 1000),
                int((start + timedelta(minutes=16)).timestamp() * 1000),
            ): 0
        }
        with tempfile.TemporaryDirectory() as root:
            result = import_mt5_oanda_tms_m1(
                rates=rates,
                start_utc=start,
                end_utc=end,
                acquired_at=end,
                artifact_root=root,
                tick_counts=ticks,
                terminal_version="build-test",
                runtime_version="test",
            )
            self.assertEqual(result["status"], "VALIDATED")
            self.assertEqual(result["quality"]["no_tick_gap_count"], 1)
            self.assertEqual(result["raw_m1_bars"], 59)
            manifest = json.loads(Path(result["manifest_path"]).read_text())
            self.assertEqual(manifest["provenance_v2"]["license_id"], "NOT_EXPLICITLY_STATED")
            self.assertEqual(manifest["quality"]["active_coverage_percent"], 98.333333)
            raw = Path(root) / "artifacts/market-data/EURUSD/M1/raw" / result["raw_m1_sha256"]
            self.assertTrue((raw / "EURUSD_M1_RAW.jsonl").is_file())
            self.assertEqual(len((raw / "EURUSD_M1_RAW.jsonl").read_text().splitlines()), 59)

    def test_tick_evidence_blocks_suspicious_gap_without_writing(self):
        start = datetime(2026, 7, 1, tzinfo=UTC)
        end = start + timedelta(minutes=30)
        rates = self._rates(start, 30, missing=(10,))
        ticks = {
            (
                int((start + timedelta(minutes=10)).timestamp() * 1000),
                int((start + timedelta(minutes=11)).timestamp() * 1000),
            ): 1
        }
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(Mt5OandaHistoryError, "quality_blocked"):
                import_mt5_oanda_tms_m1(
                    rates=rates,
                    start_utc=start,
                    end_utc=end,
                    acquired_at=end,
                    artifact_root=root,
                    tick_counts=ticks,
                )
            self.assertFalse((Path(root) / "artifacts").exists())

    def test_missing_tick_evidence_blocks_without_writing(self):
        start = datetime(2026, 7, 1, tzinfo=UTC)
        end = start + timedelta(minutes=30)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(Mt5OandaHistoryError, "gap_tick_evidence_missing"):
                import_mt5_oanda_tms_m1(
                    rates=self._rates(start, 30, missing=(10,)),
                    start_utc=start,
                    end_utc=end,
                    acquired_at=end,
                    artifact_root=root,
                    tick_counts={},
                )
            self.assertFalse((Path(root) / "artifacts").exists())

    def test_windows_launcher_is_read_only_and_does_not_load_secrets(self):
        source = (
            (Path(__file__).parents[1] / "scripts/windows/Import-ODIN-MT5-OANDA-P0.ps1")
            .read_text(encoding="utf-8")
            .lower()
        )
        self.assertIn("copy_rates_range", source)
        self.assertIn("copy_ticks_range", source)
        for forbidden in (
            "order_send",
            "order_check",
            "positions_get",
            "orders_get",
            "load_dotenv",
            "login=",
            "password=",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

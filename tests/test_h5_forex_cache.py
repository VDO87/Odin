import json
import tempfile
import unittest
from pathlib import Path

from odin.data.forex_cache import cache_forex_history


class ForexCacheTests(unittest.TestCase):
    def test_valid_history_is_cached_with_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "EURUSD.csv"
            source.write_text(
                "timestamp,open,high,low,close,volume,spread\n"
                "2026-07-01T00:00:00+00:00,1.1,1.2,1.0,1.15,10,0.0001\n"
                "2026-07-01T00:15:00+00:00,1.15,1.25,1.1,1.2,11,0.0001\n",
                encoding="utf-8",
            )
            result = cache_forex_history(
                str(source), cache_root=str(root / "cache"), symbol="EURUSD",
                timeframe="M15", source="local_csv",
            )
            metadata = json.loads(Path(str(result["metadata_path"])).read_text(encoding="utf-8"))

        self.assertEqual(result["cache_status"], "OK")
        self.assertTrue(Path(str(result["cache_path"])).name == "history.csv")
        self.assertEqual(metadata["source"], "local_csv")
        self.assertIs(result["execution_allowed"], False)

    def test_invalid_history_is_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "bad.csv"
            source.write_text("timestamp,close\n", encoding="utf-8")
            result = cache_forex_history(
                str(source), cache_root=str(root / "cache"), symbol="EURUSD",
                timeframe="M15", source="local_csv",
            )

        self.assertEqual(result["cache_status"], "BLOCKED")
        self.assertIs(result["execution_allowed"], False)


if __name__ == "__main__":
    unittest.main()

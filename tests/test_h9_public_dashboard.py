import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes
from odin.dashboard.server import build_server
from odin.data.public_observation import ingest_public_observation


class PublicDashboardTests(unittest.TestCase):
    def test_public_data_endpoint_exposes_metadata_not_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / "cache"
            ingest_public_observation(
                source="ecb", url="https://data.ecb.europa.eu/feed", body=b"hidden remote body",
                cache_root=str(cache), allowed_hosts={"data.ecb.europa.eu"}, kind="macro_data",
                retrieved_at=datetime.now(UTC),
            )
            routes = DashboardRoutes(
                log_path=str(root / "events.jsonl"), sqlite_path=str(root / "odin.sqlite"),
                public_cache_root=str(cache),
            )
            status, payload = routes.serve("/data/public")

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["records_count"], 1)
        self.assertNotIn("hidden remote body", str(payload))
        self.assertIs(payload["execution_allowed"], False)

    def test_cockpit_includes_public_data_read_only_view(self):
        page = DashboardRoutes().cockpit_html()

        self.assertIn("/data/public", page)
        self.assertIn("Public data freshness", page)
        self.assertNotIn("POST", page)

    def test_dashboard_rejects_non_local_binding(self):
        with self.assertRaises(ValueError):
            build_server(host="0.0.0.0", port=0)


if __name__ == "__main__":
    unittest.main()

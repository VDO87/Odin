import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from odin.data.oanda_history import (
    OANDA_ACCOUNT_ID_ENV,
    OANDA_API_LICENSE_ENV,
    OANDA_TOKEN_ENV,
    OandaHistoryError,
    import_oanda_practice_eurusd_m1,
    load_oanda_practice_credentials,
)


class _Response:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class OandaP0HistoryTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 7, 1, tzinfo=UTC)
        self.environment = {
            OANDA_TOKEN_ENV: "test-token-not-a-secret",
            OANDA_ACCOUNT_ID_ENV: "101-001-1234567-001",
            OANDA_API_LICENSE_ENV: "https://legal.oanda.com/?code=api_license_agreement_oau&language=en",
        }

    def _body(self, start, end):
        candles = []
        cursor = start
        index = 0
        while cursor < end:
            price = 1.10000 + index * 0.00001
            candles.append({
                "complete": True, "time": cursor.isoformat().replace("+00:00", "Z"), "volume": 10 + index,
                "bid": {"o": f"{price:.5f}", "h": f"{price + .00002:.5f}", "l": f"{price - .00002:.5f}", "c": f"{price + .00001:.5f}"},
            })
            cursor += timedelta(minutes=1)
            index += 1
        return json.dumps({"candles": candles}, separators=(",", ":")).encode()

    def test_read_only_import_pages_raw_m1_and_validated_m15(self):
        end = self.start + timedelta(minutes=30)
        requests = []

        def opener(request, *, timeout):
            self.assertEqual(request.get_method(), "GET")
            parsed = urlparse(request.full_url)
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "api-fxpractice.oanda.com")
            self.assertEqual(parsed.path, "/v3/accounts/101-001-1234567-001/instruments/EUR_USD/candles")
            query = parse_qs(parsed.query)
            self.assertEqual(query["price"], ["B"])
            self.assertEqual(query["granularity"], ["M1"])
            requests.append(query)
            return _Response(self._body(datetime.fromisoformat(query["from"][0].replace("Z", "+00:00")), datetime.fromisoformat(query["to"][0].replace("Z", "+00:00"))))

        with tempfile.TemporaryDirectory() as root, patch("odin.data.oanda_history._PAGE_MAX_MINUTES", 15):
            result = import_oanda_practice_eurusd_m1(start_utc=self.start, end_utc=end, artifact_root=root, opener=opener, acquired_at=end, environ=self.environment)
            self.assertEqual(result["status"], "VALIDATED")
            self.assertFalse(result["execution_allowed"])
            self.assertEqual(len(requests), 2)
            raw_path = Path(result["artifact_path"]).parents[1] / "M1" / "raw" / result["raw_m1_sha256"]
            self.assertEqual(len(list(raw_path.glob("page-*.json"))), 2)
            manifest = json.loads(Path(result["manifest_path"]).read_text())
            self.assertEqual(manifest["raw_m1_sha256"], result["raw_m1_sha256"])
            self.assertEqual(manifest["raw_m1_candles_count"], 30)
            self.assertEqual(manifest["acquisition_endpoint"], "GET /v3/accounts/{accountID}/instruments/EUR_USD/candles")

    def test_incomplete_or_malformed_input_never_persists(self):
        end = self.start + timedelta(minutes=15)

        def opener(request, *, timeout):
            body = json.loads(self._body(self.start, end))
            body["candles"].pop()
            return _Response(json.dumps(body).encode())

        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(OandaHistoryError, "oanda_m1_period_incomplete"):
                import_oanda_practice_eurusd_m1(start_utc=self.start, end_utc=end, artifact_root=root, opener=opener, environ=self.environment)
            self.assertFalse((Path(root) / "artifacts").exists())

    def test_credentials_fail_closed_without_values_in_exception(self):
        with self.assertRaisesRegex(OandaHistoryError, "oanda_practice_token_missing") as error:
            load_oanda_practice_credentials({OANDA_ACCOUNT_ID_ENV: "account"})
        self.assertNotIn("account", str(error.exception))

    def test_adapter_contains_no_trading_endpoint(self):
        source = Path(__file__).parents[1] / "src" / "odin" / "data" / "oanda_history.py"
        content = source.read_text(encoding="utf-8").lower()
        for endpoint in ("/orders", "/trades", "/positions", "/transactions"):
            with self.subTest(endpoint=endpoint):
                self.assertNotIn(endpoint, content)


if __name__ == "__main__":
    unittest.main()

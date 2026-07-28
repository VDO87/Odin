import tempfile
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request

from odin.data.ecb_exchange_rates import fetch_ecb_exchange_rate


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, amount: int = -1) -> bytes:
        return self.payload


class EcbExchangeRateTests(unittest.TestCase):
    def test_allowed_ecb_series_is_fetched_with_pinned_accept_header(self):
        requests: list[Request] = []

        def opener(request: Request, timeout: float) -> FakeResponse:
            requests.append(request)
            self.assertEqual(timeout, 5.0)
            return FakeResponse(b"KEY,FREQ,TIME_PERIOD,OBS_VALUE\nEXR,D,2026-07-28,1.17\n")

        with tempfile.TemporaryDirectory() as tmp:
            result = fetch_ecb_exchange_rate(
                series_key="D.USD.EUR.SP00.A", cache_root=tmp, timeout_seconds=5.0, opener=opener,
            )
            metadata = Path(str(result["cache_path"])).read_text(encoding="utf-8")

        self.assertEqual(result["status"], "OK")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].full_url.split("?")[0], "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A")
        self.assertEqual(requests[0].get_header("Accept"), "application/vnd.ecb.data+csv;version=1.0.0")
        self.assertNotIn("OBS_VALUE", metadata)
        self.assertIs(result["safe_to_trade"], False)

    def test_unknown_series_is_rejected_before_network_access(self):
        def forbidden_opener(request: Request, timeout: float) -> FakeResponse:
            raise AssertionError("network must not be reached")

        result = fetch_ecb_exchange_rate(
            series_key="D.USD.GBP.SP00.A", cache_root="/tmp/unused", opener=forbidden_opener,
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "ecb_series_key_not_allowed")
        self.assertIs(result["execution_allowed"], False)

    def test_provider_failure_is_a_fail_closed_event(self):
        def opener(request: Request, timeout: float) -> FakeResponse:
            raise URLError("offline")

        result = fetch_ecb_exchange_rate(
            series_key="M.USD.EUR.SP00.A", cache_root="/tmp/unused", opener=opener,
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["events"], ["public_data.failure"])
        self.assertIs(result["llm_payload_allowed"], False)


if __name__ == "__main__":
    unittest.main()

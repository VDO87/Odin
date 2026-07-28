"""Official ECB exchange-rate observation adapter with bounded HTTP behaviour.

It retrieves one explicitly requested ECB EXR series and delegates storage to the
public-observation contract. It does not interpret rates, create signals, or
expose a generic web client.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from odin.data.public_observation import fetch_public_observation, ingest_public_observation

ECB_HOST = "data-api.ecb.europa.eu"
ECB_SERIES_RE = re.compile(r"^[DM]\.[A-Z]{3}\.EUR\.SP00\.A$")
MAX_RESPONSE_BYTES = 2_000_000


class Response(Protocol):
    def __enter__(self) -> "Response": ...

    def __exit__(self, *args: object) -> None: ...

    def read(self, amount: int = -1) -> bytes: ...


class NoRedirect(HTTPRedirectHandler):
    """Reject all redirects so a trusted host cannot pivot the connection."""

    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None


def fetch_ecb_exchange_rate(
    *,
    series_key: str,
    cache_root: str,
    timeout_seconds: float = 10.0,
    opener: Callable[[Request, float], Response] | None = None,
) -> dict[str, object]:
    """Fetch a single ECB EXR CSV observation, bounded to the official endpoint."""
    if not ECB_SERIES_RE.fullmatch(series_key):
        return _blocked("ecb_series_key_not_allowed")
    url = (
        f"https://{ECB_HOST}/service/data/EXR/{series_key}"
        "?format=csvdata&lastNObservations=1"
    )
    transport = opener or _default_open

    def fetcher(request_url: str, timeout: float) -> bytes:
        request = Request(
            request_url,
            headers={"Accept": "application/vnd.ecb.data+csv;version=1.0.0", "User-Agent": "ODIN/0.1"},
            method="GET",
        )
        try:
            with transport(request, timeout) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
        except (HTTPError, URLError, OSError, TimeoutError) as error:
            raise OSError("official_public_source_unavailable") from error
        if len(payload) > MAX_RESPONSE_BYTES:
            raise OSError("official_public_response_too_large")
        return payload

    fetched = fetch_public_observation(
        url=url, allowed_hosts={ECB_HOST}, timeout_seconds=timeout_seconds, fetcher=fetcher,
    )
    if fetched["status"] != "OK":
        return {**fetched, "component": "ecb_exchange_rates", "source": "ecb_exr"}
    return ingest_public_observation(
        source="ecb_exr", url=url, body=fetched["body"], cache_root=cache_root,
        allowed_hosts={ECB_HOST}, kind="macro_data",
    )


def _default_open(request: Request, timeout: float) -> Response:
    return build_opener(NoRedirect()).open(request, timeout=timeout)


def _blocked(reason: str) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "component": "ecb_exchange_rates",
        "mode": "READ_ONLY_PUBLIC_DATA",
        "reason": reason,
        "events": ["public_data.failure"],
        "llm_payload_allowed": False,
        "safe_to_use_for_decision": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }

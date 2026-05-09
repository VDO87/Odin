from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from external_data.models import EconomicEvent
from shared.utils import make_id, utc_now


class TradingEconomicsProvider:
    name = "TradingEconomics"

    def __init__(self, *, api_key: str | None = None, timeout_seconds: float = 5.0) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("TRADING_ECONOMICS_API_KEY", "")
        self._timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self._api_key.strip())

    def fetch_calendar(self) -> list[EconomicEvent]:
        self._assert_configured()
        payload = self._request(path="/calendar")
        events: list[EconomicEvent] = []
        for item in payload if isinstance(payload, list) else []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("Event", "")).strip() or "Unnamed macro event"
            country = str(item.get("Country", "")).strip() or "n/d"
            date_raw = str(item.get("Date", "")).strip()
            event_time = _parse_te_datetime(date_raw)
            importance = str(item.get("Importance", "")).strip().lower()
            impact = "high" if importance in {"3", "high"} else "medium"
            events.append(
                EconomicEvent(
                    event_id=make_id("te-event"),
                    provider=self.name,
                    title=title,
                    country=country,
                    event_time_utc=event_time,
                    impact=impact,
                    actual=_string_or_none(item.get("Actual")),
                    forecast=_string_or_none(item.get("Forecast")),
                    previous=_string_or_none(item.get("Previous")),
                )
            )
        return events

    def _assert_configured(self) -> None:
        if not self.is_configured():
            raise ValueError("trading_economics_api_key_missing")

    def _request(self, *, path: str) -> object:
        query = urlencode({"c": self._api_key, "f": "json"})
        url = f"https://api.tradingeconomics.com{path}?{query}"
        try:
            with urlopen(url, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except URLError as error:
            raise RuntimeError(f"trading_economics_request_failed:{error}") from error


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _parse_te_datetime(value: str):
    # TE date formats can vary. Fallback to now on parse issues.
    if not value:
        return utc_now()
    from datetime import datetime

    candidates = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in candidates:
        try:
            parsed = datetime.strptime(value.split("Z")[0], fmt)
            return parsed.replace(tzinfo=utc_now().tzinfo)
        except ValueError:
            continue
    return utc_now()

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from external_data.models import AssetMetadata, ExternalQuote
from shared.enums import AssetClass
from shared.utils import utc_now


class AlphaVantageProvider:
    name = "AlphaVantage"

    def __init__(self, *, api_key: str | None = None, timeout_seconds: float = 5.0) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("ALPHA_VANTAGE_API_KEY", "")
        self._timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self._api_key.strip())

    def fetch_quote(self, symbol: str) -> ExternalQuote:
        self._assert_configured()
        normalized = symbol.upper().strip() or "EURUSD"
        payload: dict[str, object]
        if len(normalized) == 6 and normalized.isalpha():
            payload = self._request(
                {
                    "function": "CURRENCY_EXCHANGE_RATE",
                    "from_currency": normalized[:3],
                    "to_currency": normalized[3:],
                }
            )
            quote_raw = payload.get("Realtime Currency Exchange Rate", {})
            fx_quote: dict[str, Any] = quote_raw if isinstance(quote_raw, dict) else {}
            bid = _to_float(fx_quote.get("8. Bid Price"))
            ask = _to_float(fx_quote.get("9. Ask Price"))
            last = _to_float(fx_quote.get("5. Exchange Rate"))
            return ExternalQuote(
                symbol=normalized,
                provider=self.name,
                timestamp_utc=utc_now(),
                bid=bid,
                ask=ask,
                last_price=last,
                currency=normalized[3:],
            )

        payload = self._request({"function": "GLOBAL_QUOTE", "symbol": normalized})
        quote_raw = payload.get("Global Quote", {})
        equity_quote: dict[str, Any] = quote_raw if isinstance(quote_raw, dict) else {}
        last = _to_float(equity_quote.get("05. price"))
        return ExternalQuote(
            symbol=normalized,
            provider=self.name,
            timestamp_utc=utc_now(),
            last_price=last,
        )

    def search_assets(self, query: str) -> list[AssetMetadata]:
        self._assert_configured()
        payload = self._request({"function": "SYMBOL_SEARCH", "keywords": query.strip()})
        matches = payload.get("bestMatches", [])
        results: list[AssetMetadata] = []
        for item in matches if isinstance(matches, list) else []:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("1. symbol", "")).strip().upper()
            name = str(item.get("2. name", "")).strip() or symbol
            asset_type_raw = str(item.get("3. type", "")).strip().upper()
            region = str(item.get("4. region", "")).strip() or None
            currency = str(item.get("8. currency", "")).strip() or None
            asset_class = _asset_class_from_alpha_type(asset_type_raw)
            if not symbol:
                continue
            results.append(
                AssetMetadata(
                    symbol=symbol,
                    provider=self.name,
                    name=name,
                    asset_class=asset_class,
                    currency=currency,
                    exchange=region,
                )
            )
        return results

    def _assert_configured(self) -> None:
        if not self.is_configured():
            raise ValueError("alpha_vantage_api_key_missing")

    def _request(self, params: dict[str, str]) -> dict[str, object]:
        query = dict(params)
        query["apikey"] = self._api_key
        url = f"https://www.alphavantage.co/query?{urlencode(query)}"
        try:
            with urlopen(url, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except URLError as error:
            raise RuntimeError(f"alpha_vantage_request_failed:{error}") from error
        if not isinstance(payload, dict):
            raise RuntimeError("alpha_vantage_invalid_payload")
        if "Error Message" in payload:
            raise RuntimeError(f"alpha_vantage_error:{payload['Error Message']}")
        if "Note" in payload:
            raise RuntimeError(f"alpha_vantage_rate_note:{payload['Note']}")
        return payload


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value))
    except ValueError:
        return None


def _asset_class_from_alpha_type(value: str) -> AssetClass:
    mapping = {
        "EQUITY": AssetClass.STOCK,
        "ETF": AssetClass.ETF,
        "CRYPTO": AssetClass.CRYPTO,
        "FOREX": AssetClass.FOREX,
    }
    return mapping.get(value, AssetClass.STOCK)

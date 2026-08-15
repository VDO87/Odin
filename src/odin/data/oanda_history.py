"""Read-only OANDA Practice historical-candle acquisition for P0."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from odin.contracts.historical_candles import CANONICAL_CANDLE_COLUMNS, CANONICAL_CANDLE_SCHEMA_VERSION
from odin.data.canonical_candle_history import canonical_dataset_hash, import_canonical_candle_history
from odin.data.dukascopy_history import DukascopyHistoryError, aggregate_m1_to_m15

OANDA_PRACTICE_API_BASE = "https://api-fxpractice.oanda.com"
OANDA_CANDLES_PATH = "/v3/accounts/{account_id}/instruments/EUR_USD/candles"
OANDA_API_DOCUMENTATION_URL = "https://developer.oanda.com/rest-live-v20/pricing-ep/"
OANDA_API_LICENSE_ENV = "ODIN_OANDA_PRACTICE_API_LICENSE_URL"
OANDA_ACCOUNT_ID_ENV = "ODIN_OANDA_PRACTICE_ACCOUNT_ID"
OANDA_TOKEN_ENV = "ODIN_OANDA_PRACTICE_TOKEN"
OANDA_INSTRUMENT = "EUR_USD"
OANDA_PRICE_COMPONENT = "B"
OANDA_GRANULARITY = "M1"
_M1 = timedelta(minutes=1)
_PAGE_MAX_MINUTES = 4_999


class OandaHistoryError(ValueError):
    """OANDA input, response, or provenance is unsuitable for P0."""


def load_oanda_practice_credentials(environ: dict[str, str] | None = None) -> tuple[str, str, str]:
    """Load required local-only values without ever including values in errors."""
    values = environ if environ is not None else os.environ
    token = values.get(OANDA_TOKEN_ENV, "").strip()
    account_id = values.get(OANDA_ACCOUNT_ID_ENV, "").strip()
    license_url = values.get(OANDA_API_LICENSE_ENV, "").strip()
    if not token:
        raise OandaHistoryError("oanda_practice_token_missing")
    if not account_id:
        raise OandaHistoryError("oanda_practice_account_id_missing")
    if not _is_oanda_legal_url(license_url):
        raise OandaHistoryError("oanda_practice_api_license_url_invalid")
    return token, account_id, license_url


def _is_oanda_legal_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.netloc in {"legal.oanda.com", "www.oanda.com"} and bool(parsed.path)


def _utc_minute(value: datetime, *, error_code: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise OandaHistoryError(error_code)
    value = value.astimezone(UTC)
    if value.second or value.microsecond:
        raise OandaHistoryError(error_code)
    return value


def _utc_second(value: datetime, *, error_code: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise OandaHistoryError(error_code)
    return value.astimezone(UTC).replace(microsecond=0)


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise OandaHistoryError("oanda_candle_timestamp_invalid") from error
    return _utc_minute(parsed, error_code="oanda_candle_timestamp_not_utc")


def _request_url(account_id: str, start: datetime, end: datetime) -> str:
    path = OANDA_CANDLES_PATH.format(account_id=account_id)
    query = urlencode(
        {
            "from": start.isoformat().replace("+00:00", "Z"),
            "to": end.isoformat().replace("+00:00", "Z"),
            "price": OANDA_PRICE_COMPONENT,
            "granularity": OANDA_GRANULARITY,
        }
    )
    return f"{OANDA_PRACTICE_API_BASE}{path}?{query}"


def _read_page(url: str, token: str, *, timeout_seconds: float, opener: Callable[..., Any]) -> bytes:
    request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, method="GET")
    try:
        with opener(request, timeout=timeout_seconds) as response:  # nosec B310 - fixed OANDA Practice HTTPS origin
            return response.read()
    except (HTTPError, URLError, OSError) as error:
        raise OandaHistoryError("oanda_candles_unavailable") from error


def _decode_page(raw: bytes) -> list[dict[str, float | int]]:
    try:
        payload = json.loads(raw.decode("utf-8"))
        candles = payload["candles"]
    except (UnicodeDecodeError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise OandaHistoryError("oanda_candles_response_invalid") from error
    if not isinstance(candles, list):
        raise OandaHistoryError("oanda_candles_response_invalid")
    result: list[dict[str, float | int]] = []
    for source in candles:
        try:
            if source["complete"] is not True:
                raise ValueError("incomplete")
            timestamp = _timestamp(source["time"])
            bid = source["bid"]
            candle = {
                "timestamp_ms": int(timestamp.timestamp() * 1000),
                "open": float(bid["o"]),
                "high": float(bid["h"]),
                "low": float(bid["l"]),
                "close": float(bid["c"]),
                "volume": float(source["volume"]),
            }
        except (KeyError, TypeError, ValueError) as error:
            raise OandaHistoryError("oanda_candle_invalid") from error
        if not all(math.isfinite(float(candle[key])) for key in ("open", "high", "low", "close", "volume")):
            raise OandaHistoryError("oanda_candle_non_finite")
        if candle["volume"] < 0 or candle["low"] > min(candle["open"], candle["close"]) or candle["high"] < max(candle["open"], candle["close"]):
            raise OandaHistoryError("oanda_candle_ohlcv_invalid")
        result.append(candle)
    return result


def _validate_m1_coverage(candles: list[dict[str, float | int]], *, start: datetime, end: datetime) -> list[dict[str, object]]:
    if not candles:
        raise OandaHistoryError("oanda_m1_empty")
    expected_first = int(start.timestamp() * 1000)
    expected_last = int((end - _M1).timestamp() * 1000)
    if int(candles[0]["timestamp_ms"]) != expected_first or int(candles[-1]["timestamp_ms"]) != expected_last:
        raise OandaHistoryError("oanda_m1_period_incomplete")
    gaps: list[dict[str, object]] = []
    previous = int(candles[0]["timestamp_ms"])
    for candle in candles[1:]:
        current = int(candle["timestamp_ms"])
        if current <= previous:
            raise OandaHistoryError("oanda_m1_ordering_invalid")
        delta = current - previous
        if delta != 60_000:
            before = datetime.fromtimestamp(previous / 1000, UTC)
            after = datetime.fromtimestamp(current / 1000, UTC)
            if before.weekday() != 4 or after.weekday() != 6 or delta > 60 * 60 * 1000:
                raise OandaHistoryError("oanda_m1_gap_incompatible")
            gaps.append({"from_utc": before.isoformat().replace("+00:00", "Z"), "to_utc": after.isoformat().replace("+00:00", "Z"), "duration_seconds": delta // 1000})
        previous = current
    return gaps


def _raw_bundle_hash(pages: list[bytes]) -> str:
    digest = hashlib.sha256()
    for page in pages:
        digest.update(len(page).to_bytes(8, "big"))
        digest.update(page)
    return digest.hexdigest()


def _write_raw_bundle(root: Path, pages: list[bytes], *, acquisition: dict[str, object]) -> tuple[str, str]:
    digest = _raw_bundle_hash(pages)
    raw_dir = root / "artifacts" / "market-data" / "EURUSD" / "M1" / "raw" / digest
    if raw_dir.exists():
        expected = [raw_dir / f"page-{index:03d}.json" for index in range(1, len(pages) + 1)]
        if len(list(raw_dir.glob("page-*.json"))) != len(pages) or any(path.read_bytes() != page for path, page in zip(expected, pages)):
            raise OandaHistoryError("oanda_raw_hash_collision")
        return digest, str(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=False)
    page_hashes = []
    for index, page in enumerate(pages, start=1):
        filename = f"page-{index:03d}.json"
        path = raw_dir / filename
        path.write_bytes(page)
        page_hashes.append({"file": filename, "sha256": hashlib.sha256(page).hexdigest(), "bytes": len(page)})
    (raw_dir / "manifest.json").write_text(json.dumps({**acquisition, "raw_sha256": digest, "pages": page_hashes}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return digest, str(raw_dir)


def _canonical_m15_rows(m15: list[dict[str, float | int]], *, provenance: str, license_url: str) -> list[dict[str, str]]:
    rows = [
        {
            "symbol": "EURUSD", "timeframe": "M15",
            "timestamp_utc": datetime.fromtimestamp(int(candle["timestamp_ms"]) / 1000, UTC).isoformat().replace("+00:00", "Z"),
            "open": f"{float(candle['open']):.5f}", "high": f"{float(candle['high']):.5f}",
            "low": f"{float(candle['low']):.5f}", "close": f"{float(candle['close']):.5f}",
            "volume": f"{float(candle['volume']):.6f}", "source": "OANDA v20 Practice candles",
            "source_version": "OANDA v20 REST; GET candles; price=B; granularity=M1",
            "schema_version": CANONICAL_CANDLE_SCHEMA_VERSION, "provenance": provenance,
            "license": f"OANDA API License Agreement: {license_url}",
        }
        for candle in m15
    ]
    digest = canonical_dataset_hash(rows)
    return [dict(row, hash=digest) for row in rows]


def import_oanda_practice_eurusd_m1(
    *, start_utc: datetime, end_utc: datetime, artifact_root: str | Path, timeout_seconds: float = 20.0,
    opener: Callable[..., Any] = urlopen, acquired_at: datetime | None = None, environ: dict[str, str] | None = None,
) -> dict[str, object]:
    """Fetch P0 via fixed read-only Practice candle requests and persist only after validation."""
    start = _utc_minute(start_utc, error_code="oanda_period_not_utc")
    end = _utc_minute(end_utc, error_code="oanda_period_not_utc")
    if start >= end or (end - start) % _M1:
        raise OandaHistoryError("oanda_period_invalid")
    token, account_id, license_url = load_oanda_practice_credentials(environ)
    pages: list[bytes] = []
    candles: list[dict[str, float | int]] = []
    cursor = start
    while cursor < end:
        page_end = min(cursor + timedelta(minutes=_PAGE_MAX_MINUTES), end)
        raw = _read_page(_request_url(account_id, cursor, page_end), token, timeout_seconds=timeout_seconds, opener=opener)
        pages.append(raw)
        page_candles = _decode_page(raw)
        if any(not (int(candle["timestamp_ms"]) >= int(cursor.timestamp() * 1000) and int(candle["timestamp_ms"]) < int(page_end.timestamp() * 1000)) for candle in page_candles):
            raise OandaHistoryError("oanda_page_outside_requested_window")
        candles.extend(page_candles)
        cursor = page_end
    gaps = _validate_m1_coverage(candles, start=start, end=end)
    try:
        m15 = aggregate_m1_to_m15(candles)
    except DukascopyHistoryError as error:
        raise OandaHistoryError(str(error).replace("dukascopy", "oanda")) from error
    acquired = _utc_second(acquired_at or datetime.now(UTC), error_code="oanda_acquired_at_not_utc")
    raw_hash = _raw_bundle_hash(pages)
    provenance = (
        f"api_base={OANDA_PRACTICE_API_BASE}; endpoint=GET_candles_only; instrument={OANDA_INSTRUMENT}; "
        f"price_component=BID; price_parameter={OANDA_PRICE_COMPONENT}; granularity={OANDA_GRANULARITY}; timezone=UTC; "
        f"period=[{start.isoformat().replace('+00:00', 'Z')},{end.isoformat().replace('+00:00', 'Z')}); "
        f"acquired_at={acquired.isoformat().replace('+00:00', 'Z')}; raw_m1_sha256={raw_hash}; "
        "aggregation=M1_to_M15_UTC_complete_windows_v1"
    )
    rows = _canonical_m15_rows(m15, provenance=provenance, license_url=license_url)
    root = Path(artifact_root)
    try:
        raw_hash, raw_path = _write_raw_bundle(root, pages, acquisition={
            "source": "OANDA v20 Practice", "api_base": OANDA_PRACTICE_API_BASE,
            "endpoint": "GET /v3/accounts/{accountID}/instruments/EUR_USD/candles", "instrument": OANDA_INSTRUMENT,
            "price_component": "BID", "price_parameter": OANDA_PRICE_COMPONENT, "timeframe": OANDA_GRANULARITY,
            "timezone": "UTC", "period_start_utc": start.isoformat().replace("+00:00", "Z"),
            "period_end_utc": end.isoformat().replace("+00:00", "Z"), "acquired_at_utc": acquired.isoformat().replace("+00:00", "Z"),
            "api_documentation_url": OANDA_API_DOCUMENTATION_URL, "license": f"OANDA API License Agreement: {license_url}",
            "candles_count": len(candles), "gaps": gaps,
        })
    except (OSError, OandaHistoryError) as error:
        return {"status": "BLOCKED", "component": "oanda_history", "reason": "oanda_artifact_persistence_failed", "detail": type(error).__name__, "safe_to_trade": False, "real_trading": False, "execution_allowed": False}
    with tempfile.TemporaryDirectory(prefix="odin-oanda-") as temporary:
        canonical_path = Path(temporary) / "EURUSD_M15_oanda_canonical.csv"
        with canonical_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CANONICAL_CANDLE_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        result = import_canonical_candle_history(
            canonical_path, symbol="EURUSD", timeframe="M15", artifact_root=root, ingested_at=acquired,
            manifest_extras={
                "raw_m1_sha256": raw_hash, "raw_m1_artifact_path": raw_path, "raw_m1_pages": len(pages),
                "raw_m1_candles_count": len(candles), "raw_m1_gaps": gaps,
                "acquisition_endpoint": "GET /v3/accounts/{accountID}/instruments/EUR_USD/candles",
            },
        )
        if result["status"] != "VALIDATED":
            return result
    return {**result, "component": "oanda_history", "raw_m1_sha256": raw_hash, "raw_m1_candles_count": len(candles), "raw_m1_gaps": gaps, "source_rows_m1": len(candles), "pages": len(pages), "acquired_at_utc": acquired.isoformat().replace("+00:00", "Z")}

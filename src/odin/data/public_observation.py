"""Fail-closed ingestion contract for public, read-only market observations.

This module deliberately has no network client. A provider adapter must inject a
bounded fetcher after validating its own official API configuration. Remote text
is never returned, persisted, or passed to an LLM: it is untrusted evidence only.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

MAX_BODY_BYTES = 2_000_000
MAX_TIMEOUT_SECONDS = 30.0
SOURCE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
OBSERVATION_KINDS = frozenset({"news", "official_release", "macro_data"})


def ingest_public_observation(
    *,
    source: str,
    url: str,
    body: bytes | str,
    cache_root: str,
    allowed_hosts: set[str] | frozenset[str],
    kind: str,
    retrieved_at: datetime | None = None,
    published_at: datetime | None = None,
) -> dict[str, object]:
    """Store metadata for one permitted public response without retaining its text."""
    reason, redacted_url = _validate_source(source, url, allowed_hosts, kind)
    if reason:
        return _blocked(reason)
    content = body.encode("utf-8") if isinstance(body, str) else body
    if not content:
        return _blocked("public_content_empty")
    if len(content) > MAX_BODY_BYTES:
        return _blocked("public_content_too_large")

    digest = hashlib.sha256(content).hexdigest()
    observed_at = _utc_iso(retrieved_at or datetime.now(UTC))
    publication = _utc_iso(published_at) if published_at else None
    target = Path(cache_root) / source / digest / "observation.json"
    duplicate = target.exists()
    if not duplicate:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "content_classification": "untrusted_public_content",
                    "content_hash": digest,
                    "content_length": len(content),
                    "kind": kind,
                    "published_at": publication,
                    "retrieved_at": observed_at,
                    "source": source,
                    "source_url": redacted_url,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    return {
        "status": "OK",
        "component": "public_observation",
        "mode": "READ_ONLY_PUBLIC_DATA",
        "source": source,
        "source_url": redacted_url,
        "kind": kind,
        "content_hash": digest,
        "content_length": len(content),
        "retrieved_at": observed_at,
        "published_at": publication,
        "cache_path": str(target),
        "duplicate": duplicate,
        "events": ["public_data.duplicate" if duplicate else "public_data.cached"],
        "content_classification": "untrusted_public_content",
        "llm_payload_allowed": False,
        "safe_to_use_for_decision": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def fetch_public_observation(
    *,
    url: str,
    allowed_hosts: set[str] | frozenset[str],
    timeout_seconds: float,
    fetcher: Callable[[str, float], bytes | str],
) -> dict[str, object]:
    """Call an injected provider transport with a bounded timeout, never a browser."""
    if not 0 < timeout_seconds <= MAX_TIMEOUT_SECONDS:
        return _blocked("public_timeout_invalid")
    reason, redacted_url = _validate_url(url, allowed_hosts)
    if reason:
        return _blocked(reason)
    try:
        body = fetcher(url, timeout_seconds)
    except (OSError, TimeoutError, ValueError):
        return _blocked("public_provider_fetch_failed", source_url=redacted_url)
    if not isinstance(body, (bytes, str)):
        return _blocked("public_provider_response_invalid", source_url=redacted_url)
    return {"status": "OK", "source_url": redacted_url, "body": body}


def assess_public_freshness(
    observation: dict[str, object], *, max_age_seconds: int, now: datetime | None = None,
) -> dict[str, object]:
    """Apply a freshness gate without interpreting the content as advice or a signal."""
    if observation.get("status") != "OK" or max_age_seconds <= 0:
        return _freshness_blocked("public_observation_not_available")
    try:
        retrieved = datetime.fromisoformat(str(observation["retrieved_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return _freshness_blocked("public_observation_timestamp_invalid")
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    age_seconds = max(0, int((reference - retrieved).total_seconds()))
    fresh = age_seconds <= max_age_seconds
    return {
        "status": "OK" if fresh else "WARNING",
        "component": "public_observation_freshness",
        "mode": "READ_ONLY_PUBLIC_DATA",
        "age_seconds": age_seconds,
        "max_age_seconds": max_age_seconds,
        "fresh": fresh,
        "gap_detected": not fresh,
        "events": [] if fresh else ["public_data.stale"],
        "safe_to_use_for_decision": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _validate_source(
    source: str, url: str, allowed_hosts: set[str] | frozenset[str], kind: str,
) -> tuple[str | None, str | None]:
    if not SOURCE_RE.fullmatch(source):
        return "public_source_name_invalid", None
    if kind not in OBSERVATION_KINDS:
        return "public_kind_not_allowed", None
    return _validate_url(url, allowed_hosts)


def _validate_url(url: str, allowed_hosts: set[str] | frozenset[str]) -> tuple[str | None, str | None]:
    parsed = urlsplit(url)
    hosts = {host.lower() for host in allowed_hosts}
    if parsed.scheme != "https" or parsed.username or parsed.password or not parsed.hostname:
        return "public_source_url_invalid", None
    if parsed.hostname.lower() not in hosts:
        return "public_source_host_not_allowed", None
    return None, urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="seconds")


def _blocked(reason: str, **extra: object) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "component": "public_observation",
        "mode": "READ_ONLY_PUBLIC_DATA",
        "reason": reason,
        "events": ["public_data.failure"],
        **extra,
        "llm_payload_allowed": False,
        "safe_to_use_for_decision": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }


def _freshness_blocked(reason: str) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "component": "public_observation_freshness",
        "mode": "READ_ONLY_PUBLIC_DATA",
        "reason": reason,
        "events": ["public_data.failure"],
        "safe_to_use_for_decision": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }

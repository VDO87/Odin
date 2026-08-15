"""Hermes-compatible context input with no authority over factual or risk state."""

from __future__ import annotations

from odin.contracts.shadow_intelligence import ContextPacket


def context_from_public_observation(value: dict[str, object], *, affected_assets: tuple[str, ...] = ("EURUSD",)) -> ContextPacket:
    status = "VALID" if value.get("status") == "OK" and value.get("fresh") is True else "STALE" if value.get("status") == "OK" else "UNAVAILABLE"
    source = str(value.get("source", "unknown"))
    timestamp = str(value.get("retrieved_at", value.get("timestamp", "")))
    evidence = (str(value.get("latest_content_hash", value.get("content_hash", "UNAVAILABLE"))),)
    return ContextPacket(source, timestamp, evidence, None, affected_assets, "UNSPECIFIED", ("context_is_non_authoritative",), "FRESH" if status == "VALID" else "STALE", str(value.get("source_url", "UNAVAILABLE")), status)

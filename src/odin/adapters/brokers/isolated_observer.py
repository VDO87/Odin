"""Fail-closed capability guard for a future isolated observer runtime."""

from __future__ import annotations

from collections.abc import Mapping

ALLOWED_CAPABILITIES = frozenset({"account_summary", "open_positions", "trade_history"})


def observer_status(*, enabled: bool = False, runtime_available: bool = False) -> dict[str, object]:
    """Report unavailable until a separately approved isolated runtime exists."""
    reason = "observer_disabled"
    if enabled and not runtime_available:
        reason = "observer_runtime_not_available"
    return {
        "status": "BLOCKED",
        "component": "isolated_observer",
        "mode": "LOCAL_READ_ONLY_OBSERVER",
        "reason": reason,
        "enabled": False,
        "runtime_available": False,
        "supported_capabilities": sorted(ALLOWED_CAPABILITIES),
        "generic_navigation_allowed": False,
        "generic_input_allowed": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
        "next_safe_action": "operator_review_isolated_observer",
    }


def validate_observer_request(request: Mapping[str, object]) -> dict[str, object]:
    """Accept only a known read-only capability and no free-form controls."""
    capability = request.get("capability")
    keys = set(request)
    allowed_keys = {"capability", "request_id"}
    if keys - allowed_keys:
        return _blocked("observer_request_contains_unapproved_fields")
    if not isinstance(capability, str) or capability not in ALLOWED_CAPABILITIES:
        return _blocked("observer_capability_not_allowed")
    request_id = request.get("request_id")
    if request_id is not None and (not isinstance(request_id, str) or not request_id.strip()):
        return _blocked("observer_request_id_invalid")
    return {
        "status": "BLOCKED",
        "component": "isolated_observer",
        "mode": "LOCAL_READ_ONLY_OBSERVER",
        "reason": "observer_runtime_not_enabled",
        "capability": capability,
        "request_id": request_id or "not_supplied",
        "validated_read_only_request": True,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
        "next_safe_action": "await_operator_approval_for_isolated_runtime",
    }


def _blocked(reason: str) -> dict[str, object]:
    return {
        "status": "BLOCKED",
        "component": "isolated_observer",
        "mode": "LOCAL_READ_ONLY_OBSERVER",
        "reason": reason,
        "validated_read_only_request": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }

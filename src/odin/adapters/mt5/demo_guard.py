"""Strict, read-only guard for supervised MT5 demo preparation."""

from __future__ import annotations


def demo_account_guard(account_mode: str | None) -> dict[str, object]:
    """Classify a requested account mode without connecting to a terminal."""
    normalized = (account_mode or "").strip().lower()
    accepted = normalized == "demo"
    reason = "demo_account_required" if not accepted else "demo_configuration_pending_operator_review"
    if normalized == "real":
        reason = "real_account_mode_rejected"
    elif normalized and not accepted:
        reason = "unknown_account_mode_rejected"

    return {
        "component": "mt5_demo_guard",
        "status": "READY_FOR_REVIEW" if accepted else "BLOCKED",
        "requested_account_mode": normalized or "missing",
        "account_mode_accepted": accepted,
        "terminal_connection_attempted": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
        "reason": reason,
        "next_safe_action": (
            "operator_review_demo_configuration"
            if accepted
            else "set_ODIN_MT5_ACCOUNT_MODE_to_demo"
        ),
    }

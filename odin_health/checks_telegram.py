from __future__ import annotations

import os
from typing import Any


def check_telegram() -> dict[str, Any]:
    enabled = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    allowed = os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").strip()

    configured = bool(token and allowed)
    status = "OK"
    if enabled and not configured:
        status = "WARNING"

    return {
        "status": status,
        "enabled": enabled,
        "configured": configured,
    }

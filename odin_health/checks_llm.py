from __future__ import annotations

import os
from typing import Any


def check_local_llm() -> dict[str, Any]:
    enabled = os.getenv("LOCAL_LLM_ENABLED", "true").lower() == "true"
    provider = os.getenv("LOCAL_LLM_PROVIDER", "ollama").strip()
    base_url = os.getenv("LOCAL_LLM_BASE_URL", "").strip()
    model = os.getenv("LOCAL_LLM_MODEL", "").strip()

    configured = bool(base_url)
    status = "OK"
    if enabled and not configured:
        status = "WARNING"
    if enabled and provider.lower() == "openai":
        status = "CRITICAL"

    return {
        "status": status,
        "enabled": enabled,
        "provider": provider,
        "configured": configured,
        "model": model,
    }

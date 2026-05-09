from __future__ import annotations

import os
from typing import Any

from odin_assistant.local_llm_interface import LocalLLMInterface


def check_local_llm() -> dict[str, Any]:
    enabled = os.getenv("LOCAL_LLM_ENABLED", "true").lower() == "true"
    provider = os.getenv("LOCAL_LLM_PROVIDER", "ollama").strip() or "ollama"
    base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434").strip()
    model = os.getenv("LOCAL_LLM_MODEL", "").strip()
    timeout_seconds = int(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "30"))
    llm_required = os.getenv("ODIN_REQUIRE_LOCAL_LLM", "false").lower() == "true"

    llm = LocalLLMInterface()
    runtime = llm.healthcheck()
    runtime_status = str(runtime.get("status", "WARNING"))
    runtime_error = runtime.get("error")

    status = "OK"
    reason = "local_llm_ready"

    if not enabled:
        status = "WARNING"
        reason = "local_llm_disabled"
    elif provider.lower() != "ollama":
        status = "WARNING"
        reason = "unsupported_local_provider"
    elif not model:
        status = "WARNING"
        reason = "local_llm_model_not_configured"
    elif runtime_status != "OK":
        status = "WARNING"
        reason = "local_llm_unavailable"

    if llm_required and status == "WARNING":
        status = "BLOCKED"
        reason = "local_llm_required_but_unavailable"

    return {
        "status": status,
        "enabled": enabled,
        "provider": provider,
        "base_url": base_url,
        "model": model,
        "timeout_seconds": timeout_seconds,
        "reachable": runtime_status == "OK",
        "reason": reason,
        "error": runtime_error,
        "safe_to_trade": True,
    }

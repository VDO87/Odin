from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


class LocalLLMInterface:
    def __init__(self) -> None:
        self.enabled = os.getenv("LOCAL_LLM_ENABLED", "true").lower() == "true"
        self.provider = os.getenv("LOCAL_LLM_PROVIDER", "ollama")
        self.base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434")
        self.model = os.getenv("LOCAL_LLM_MODEL", "")

    def ask(self, prompt: str) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "reason": "local_llm_disabled"}
        if self.provider.lower() != "ollama":
            return {"ok": False, "reason": "unsupported_local_provider"}
        if not self.model:
            return {"ok": False, "reason": "local_llm_model_not_configured"}

        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode("utf-8")
        req = Request(
            url=f"{self.base_url.rstrip('/')}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=10) as response:  # nosec B310
                data = json.loads(response.read().decode("utf-8"))
            return {"ok": True, "response": data.get("response", "")}
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            return {"ok": False, "reason": f"local_llm_unavailable:{error.__class__.__name__}"}

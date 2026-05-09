from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from odin_assistant.redaction import redact_for_assistant
from odin_brain.llm_models import LLMHealth, LLMResult, now_iso


class LocalLLMRuntime:
    def __init__(self) -> None:
        self.enabled = os.getenv("LOCAL_LLM_ENABLED", "true").lower() == "true"
        self.provider = os.getenv("LOCAL_LLM_PROVIDER", "ollama").strip() or "ollama"
        self.base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434").strip()
        self.model = os.getenv("LOCAL_LLM_MODEL", "").strip()
        self.timeout_seconds = int(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "30"))
        self.max_tokens = int(os.getenv("LOCAL_LLM_MAX_TOKENS", "800"))
        self.temperature = float(os.getenv("LOCAL_LLM_TEMPERATURE", "0.2"))
        self.require_context = os.getenv("LOCAL_LLM_REQUIRE_CONTEXT", "true").lower() == "true"

    def is_enabled(self) -> bool:
        return self.enabled

    def _result(
        self,
        *,
        status: str,
        response: str = "",
        error: str | None = None,
        latency_ms: int = 0,
        used_context: bool = False,
        safe: bool = True,
    ) -> dict[str, Any]:
        return LLMResult(
            status=status,
            provider=self.provider,
            model=self.model,
            response=response,
            error=error,
            latency_ms=latency_ms,
            used_context=used_context,
            safe=safe,
            timestamp=now_iso(),
        ).to_dict()

    def _health(self, *, status: str, error: str | None = None, safe_to_trade: bool = True) -> dict[str, Any]:
        return LLMHealth(
            status=status,
            provider=self.provider,
            model=self.model,
            endpoint=self.base_url,
            enabled=self.enabled,
            error=error,
            safe_to_trade=safe_to_trade,
            timestamp=now_iso(),
        ).to_dict()

    def healthcheck(self) -> dict[str, Any]:
        if not self.enabled:
            return self._health(status="WARNING", error="local_llm_disabled", safe_to_trade=True)
        if self.provider.lower() != "ollama":
            return self._health(status="WARNING", error="unsupported_provider", safe_to_trade=True)
        if not self.model:
            return self._health(status="WARNING", error="local_llm_model_not_configured", safe_to_trade=True)

        start = time.monotonic()
        try:
            request = Request(f"{self.base_url.rstrip('/')}/api/tags", method="GET")
            with urlopen(request, timeout=self.timeout_seconds) as response:  # nosec B310
                _ = response.read().decode("utf-8")
            _ = int((time.monotonic() - start) * 1000)
            return self._health(status="OK", error=None, safe_to_trade=True)
        except (URLError, HTTPError, TimeoutError, OSError) as error:
            return self._health(status="WARNING", error=f"{error.__class__.__name__}: {error}", safe_to_trade=True)

    def list_models(self) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "WARNING", "provider": self.provider, "model": self.model, "response": [], "error": "local_llm_disabled", "latency_ms": 0, "used_context": False, "safe": True, "timestamp": now_iso()}
        if self.provider.lower() != "ollama":
            return {"status": "WARNING", "provider": self.provider, "model": self.model, "response": [], "error": "unsupported_provider", "latency_ms": 0, "used_context": False, "safe": True, "timestamp": now_iso()}

        start = time.monotonic()
        try:
            request = Request(f"{self.base_url.rstrip('/')}/api/tags", method="GET")
            with urlopen(request, timeout=self.timeout_seconds) as response:  # nosec B310
                data = json.loads(response.read().decode("utf-8"))
            latency = int((time.monotonic() - start) * 1000)
            models = [m.get("name", "") for m in data.get("models", []) if isinstance(m, dict)]
            return {
                "status": "OK",
                "provider": self.provider,
                "model": self.model,
                "response": models,
                "error": None,
                "latency_ms": latency,
                "used_context": False,
                "safe": True,
                "timestamp": now_iso(),
            }
        except (URLError, HTTPError, TimeoutError, OSError, json.JSONDecodeError) as error:
            return {
                "status": "WARNING",
                "provider": self.provider,
                "model": self.model,
                "response": [],
                "error": f"{error.__class__.__name__}: {error}",
                "latency_ms": int((time.monotonic() - start) * 1000),
                "used_context": False,
                "safe": True,
                "timestamp": now_iso(),
            }

    def _generate(self, prompt: str, *, context: dict[str, Any] | None = None, options: dict[str, Any] | None = None) -> dict[str, Any]:
        safe_context = redact_for_assistant(context or {})
        if not self.enabled:
            return self._result(status="WARNING", error="local_llm_disabled", used_context=bool(safe_context), safe=True)
        if self.provider.lower() != "ollama":
            return self._result(status="WARNING", error="unsupported_provider", used_context=bool(safe_context), safe=True)
        if not self.model:
            return self._result(status="WARNING", error="local_llm_model_not_configured", used_context=bool(safe_context), safe=True)
        if self.require_context and not safe_context:
            return self._result(status="WARNING", error="missing_required_context", used_context=False, safe=True)

        call_options = {
            "temperature": self.temperature,
            "num_predict": self.max_tokens,
        }
        if options:
            call_options.update({k: v for k, v in options.items() if v is not None})

        start = time.monotonic()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": call_options,
        }
        if safe_context:
            payload["context"] = safe_context

        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url=f"{self.base_url.rstrip('/')}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # nosec B310
                raw = json.loads(response.read().decode("utf-8"))
            latency = int((time.monotonic() - start) * 1000)
            text = str(raw.get("response", "")).strip()
            if not text:
                return self._result(
                    status="WARNING",
                    error="empty_response",
                    latency_ms=latency,
                    used_context=bool(safe_context),
                    safe=True,
                )
            return self._result(
                status="OK",
                response=text,
                error=None,
                latency_ms=latency,
                used_context=bool(safe_context),
                safe=True,
            )
        except (URLError, HTTPError, TimeoutError, OSError, json.JSONDecodeError) as error:
            return self._result(
                status="WARNING",
                error=f"{error.__class__.__name__}: {error}",
                latency_ms=int((time.monotonic() - start) * 1000),
                used_context=bool(safe_context),
                safe=True,
            )

    def generate_response(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._generate(prompt, context=context, options=options)

    def summarize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = "Resume o contexto operacional do ODIN de forma curta e técnica."
        return self._generate(prompt, context=context)

    def explain_decision(self, decision_packet: dict[str, Any]) -> dict[str, Any]:
        prompt = "Explica a decisão ATLAS, o consenso e os bloqueios de risco em linguagem técnica curta."
        return self._generate(prompt, context={"decision_packet": decision_packet})

    def safe_answer(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Responde apenas com base no contexto ODIN. "
            "Se faltarem dados, diz: Não existem dados suficientes para responder com segurança. "
            f"Pergunta: {question.strip()}"
        )
        return self._generate(prompt, context=context)

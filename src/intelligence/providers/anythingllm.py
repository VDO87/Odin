from __future__ import annotations

import json
import os
from pathlib import Path
import tomllib
from typing import Any
from urllib import error, request

from intelligence.models import AdvisoryRequest, AdvisoryResponse, AdvisorySource


class AnythingLLMProvider:
    name = "AnythingLLM"

    def __init__(
        self,
        *,
        config_path: str | Path,
        api_key: str | None = None,
        base_url: str | None = None,
        workspace_slug: str | None = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self._config_path = Path(config_path)
        self._timeout_seconds = timeout_seconds
        self._base_url = (
            base_url
            or os.getenv("ANYTHINGLLM_BASE_URL")
            or "http://127.0.0.1:3001/api/v1"
        ).rstrip("/")
        self._workspace_slug = (
            workspace_slug
            or os.getenv("ANYTHINGLLM_WORKSPACE_SLUG")
            or "odin"
        ).strip()
        self._api_key = (api_key or os.getenv("ANYTHINGLLM_API_KEY") or "").strip()
        if not self._api_key:
            self._api_key = self._read_api_key_from_secrets()

    def is_available(self) -> bool:
        return bool(self._api_key)

    def ask(self, advisory_request: AdvisoryRequest, *, context_payload: dict[str, Any]) -> AdvisoryResponse:
        if not self.is_available():
            return AdvisoryResponse(
                accepted=False,
                provider=self.name,
                advisory_only=True,
                reason_code="provider_unavailable",
            )

        prompt = self._build_prompt(advisory_request, context_payload)
        url = f"{self._base_url}/workspace/{self._workspace_slug}/chat"
        payload = json.dumps(
            {
                "message": prompt,
                "mode": "query",
            }
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        req = request.Request(url=url, data=payload, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as response:
                raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
            answer = self._extract_answer(parsed)
            if not answer:
                return AdvisoryResponse(
                    accepted=False,
                    provider=self.name,
                    advisory_only=True,
                    reason_code="provider_invalid_response",
                )
            sources = self._extract_sources(parsed)
            return AdvisoryResponse(
                accepted=True,
                provider=self.name,
                advisory_only=True,
                answer=answer,
                sources=tuple(sources),
                used_context=tuple(context_payload.keys()),
            )
        except (TimeoutError, error.URLError):
            return AdvisoryResponse(
                accepted=False,
                provider=self.name,
                advisory_only=True,
                reason_code="provider_unreachable",
            )
        except json.JSONDecodeError:
            return AdvisoryResponse(
                accepted=False,
                provider=self.name,
                advisory_only=True,
                reason_code="provider_invalid_response",
            )

    def _read_api_key_from_secrets(self) -> str:
        secret_path = self._config_path.parent / "secrets" / "odin.secrets.toml"
        if not secret_path.exists():
            return ""
        try:
            raw = tomllib.loads(secret_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return ""
        intelligence_raw = raw.get("intelligence", {})
        if not isinstance(intelligence_raw, dict):
            return ""
        api_key = intelligence_raw.get("anythingllm_api_key", "")
        return str(api_key).strip() if api_key else ""

    @staticmethod
    def _build_prompt(advisory_request: AdvisoryRequest, context_payload: dict[str, Any]) -> str:
        return (
            "You are an advisory assistant for ODIN. Advisory only. Never execute, never change state, "
            "never propose critical action without human confirmation.\n\n"
            f"Query scope: {advisory_request.query_scope}\n"
            f"Operator question: {advisory_request.question}\n\n"
            "Context (JSON):\n"
            f"{json.dumps(context_payload, ensure_ascii=True, indent=2)}"
        )

    @staticmethod
    def _extract_answer(parsed: dict[str, Any]) -> str:
        for key in ("textResponse", "response", "answer", "message"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    @staticmethod
    def _extract_sources(parsed: dict[str, Any]) -> list[AdvisorySource]:
        sources_raw = parsed.get("sources")
        if not isinstance(sources_raw, list):
            return []
        sources: list[AdvisorySource] = []
        for index, source in enumerate(sources_raw, start=1):
            if not isinstance(source, dict):
                continue
            summary = str(source.get("title") or source.get("summary") or source.get("source") or "").strip()
            if not summary:
                continue
            ref = source.get("url") or source.get("ref") or source.get("source")
            sources.append(
                AdvisorySource(
                    source_id=f"anythingllm-source-{index}",
                    kind=str(source.get("type") or "provider_source"),
                    summary=summary,
                    ref=str(ref) if ref else None,
                )
            )
        return sources


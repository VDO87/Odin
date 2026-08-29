"""Adaptador controlado entre o Hermes e o trabalhador local Ollama."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


Transport = Callable[[str, dict[str, object], float], dict[str, object]]


@dataclass(frozen=True)
class OllamaAdapterConfig:
    """Limites conservadores para uma tarefa local."""

    model: str = "qwen2.5-coder:1.5b"
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 120.0
    max_task_seconds: float = 300.0
    max_attempts: int = 2
    context_size: int = 2048
    max_output_tokens: int = 512
    temperature: float = 0.1
    json_mode: bool = False
    audit_log_path: str = "logs/hermes_ollama.jsonl"

    def __post_init__(self) -> None:
        if not self.model.strip():
            raise ValueError("model nao pode estar vazio")
        if not self.base_url.startswith(("http://127.0.0.1", "http://localhost")):
            raise ValueError("Ollama deve estar limitado ao host local")
        if self.timeout_seconds <= 0 or self.max_task_seconds <= 0:
            raise ValueError("timeouts devem ser positivos")
        if self.max_attempts not in (1, 2, 3):
            raise ValueError("max_attempts deve estar entre 1 e 3")
        if not 256 <= self.context_size <= 8192:
            raise ValueError("context_size fora dos limites permitidos")
        if not 16 <= self.max_output_tokens <= 2048:
            raise ValueError("max_output_tokens fora dos limites permitidos")
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("temperature deve estar entre 0 e 1")


class OllamaAdapter:
    """Executa tarefas locais delimitadas e devolve um resultado estruturado."""

    def __init__(
        self,
        config: OllamaAdapterConfig | None = None,
        *,
        transport: Transport | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config or OllamaAdapterConfig()
        self._transport = transport or _http_transport
        self._clock = clock

    def run(
        self,
        *,
        task_id: str,
        prompt: str,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, object]:
        if not task_id.strip():
            raise ValueError("task_id nao pode estar vazio")
        if not prompt.strip():
            raise ValueError("prompt nao pode estar vazio")

        started = self._clock()
        previous_response: str | None = None
        last_error: str | None = None

        for attempt in range(1, self.config.max_attempts + 1):
            elapsed = self._clock() - started
            if cancel_event is not None and cancel_event.is_set():
                return self._result(task_id, "failed", attempt, started, error="cancelled")
            if elapsed >= self.config.max_task_seconds:
                return self._result(task_id, "timeout", attempt, started, error="task_timeout")

            timeout = min(
                self.config.timeout_seconds,
                self.config.max_task_seconds - elapsed,
            )
            payload: dict[str, object] = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "5m",
                "options": {
                    "num_ctx": self.config.context_size,
                    "num_predict": self.config.max_output_tokens,
                    "temperature": self.config.temperature,
                },
            }
            if self.config.json_mode:
                payload["format"] = "json"

            try:
                raw = self._transport(self.config.base_url, payload, timeout)
                response = raw.get("response")
                if not isinstance(response, str) or not response.strip():
                    raise ValueError("resposta Ollama vazia ou invalida")
                if previous_response == response:
                    return self._result(
                        task_id,
                        "failed",
                        attempt,
                        started,
                        response=response,
                        error="repeated_response_no_progress",
                        raw=raw,
                    )
                previous_response = response
                return self._result(
                    task_id,
                    "success",
                    attempt,
                    started,
                    response=response,
                    raw=raw,
                )
            except TimeoutError:
                last_error = "request_timeout"
            except (OSError, ValueError, urllib.error.URLError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"

        status = "timeout" if last_error == "request_timeout" else "failed"
        return self._result(task_id, status, self.config.max_attempts, started, error=last_error)

    def _result(
        self,
        task_id: str,
        status: str,
        attempt: int,
        started: float,
        *,
        response: str = "",
        error: str | None = None,
        raw: dict[str, object] | None = None,
    ) -> dict[str, object]:
        raw = raw or {}
        result: dict[str, object] = {
            "task_id": task_id,
            "status": status,
            "model": self.config.model,
            "attempt": attempt,
            "duration_seconds": round(max(0.0, self._clock() - started), 3),
            "response": response,
            "error": error,
            "metrics": {
                "prompt_tokens": _optional_int(raw.get("prompt_eval_count")),
                "generated_tokens": _optional_int(raw.get("eval_count")),
            },
        }
        self._write_audit(result)
        return result

    def _write_audit(self, result: dict[str, object]) -> None:
        path = Path(self.config.audit_log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        safe_record = {
            "task_id": result["task_id"],
            "status": result["status"],
            "model": result["model"],
            "attempt": result["attempt"],
            "duration_seconds": result["duration_seconds"],
            "error": result["error"],
            "metrics": result["metrics"],
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(safe_record, ensure_ascii=True, sort_keys=True) + "\n")


def _http_transport(
    base_url: str,
    payload: dict[str, object],
    timeout: float,
) -> dict[str, object]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise OSError(f"Ollama HTTP {exc.code}") from exc
    except TimeoutError:
        raise
    decoded = json.loads(body)
    if not isinstance(decoded, dict):
        raise ValueError("resposta Ollama nao e um objeto JSON")
    return decoded


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None

"""Isolated, hard-bounded Ollama transport worker for RC2 Hermes analysis."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from odin.hermes.ollama_adapter import OllamaAdapter, OllamaAdapterConfig


_MAX_INPUT_BYTES = 65_536


def main() -> int:
    raw = sys.stdin.read(_MAX_INPUT_BYTES + 1)
    if len(raw.encode("utf-8", errors="replace")) > _MAX_INPUT_BYTES:
        return _fail("worker_input_too_large")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _fail("worker_input_invalid")
    if not isinstance(payload, dict):
        return _fail("worker_input_invalid")
    task_id = payload.get("task_id")
    prompt = payload.get("prompt")
    audit_log_path = os.environ.get("ODIN_HERMES_WORKER_AUDIT_LOG_PATH")
    if (
        not isinstance(task_id, str)
        or not task_id
        or not isinstance(prompt, str)
        or not prompt
        or not isinstance(audit_log_path, str)
        or not audit_log_path
    ):
        return _fail("worker_input_invalid")
    adapter = OllamaAdapter(
        OllamaAdapterConfig(
            timeout_seconds=45.0,
            max_task_seconds=50.0,
            max_attempts=1,
            context_size=2048,
            max_output_tokens=192,
            temperature=0.0,
            json_mode=True,
            audit_log_path=str(Path(audit_log_path)),
        )
    )
    result = adapter.run(task_id=task_id, prompt=prompt)
    sys.stdout.write(json.dumps(result, sort_keys=True))
    return 0


def _fail(error: str) -> int:
    sys.stdout.write(
        json.dumps(
            {
                "status": "failed",
                "model": "UNAVAILABLE",
                "duration_seconds": 0.0,
                "error": error,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

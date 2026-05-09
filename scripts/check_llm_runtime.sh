#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
fi
if [[ -z "${PYTHON_BIN:-}" ]]; then
  echo "Python não encontrado." >&2
  exit 127
fi

"$PYTHON_BIN" - <<'PY'
from __future__ import annotations

import json
import os
import socket
import urllib.request


def endpoint_ok(url: str, timeout: float = 1.0) -> bool:
    try:
        req = urllib.request.Request(url=url.rstrip("/") + "/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout):  # nosec B310
            return True
    except Exception:
        return False


base_url = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:11434")
model = os.getenv("LOCAL_LLM_MODEL", "").strip()
enabled = os.getenv("LOCAL_LLM_ENABLED", "true").lower() == "true"
provider = os.getenv("LOCAL_LLM_PROVIDER", "ollama")
ollama_bin = bool(os.system("command -v ollama >/dev/null 2>&1") == 0)
models_dir = os.getenv("OLLAMA_MODELS", os.path.expandvars("${ODIN_MODELS_DIR}/ollama"))

status = {
    "status": "WARNING",
    "local_llm_enabled": enabled,
    "provider": provider,
    "base_url": base_url,
    "model_configured": bool(model),
    "ollama_installed": ollama_bin,
    "endpoint_reachable": endpoint_ok(base_url),
    "ollama_models_path": models_dir,
    "fallback_active": True,
    "installs_models_automatically": False,
}
if enabled and status["endpoint_reachable"] and status["model_configured"]:
    status["status"] = "OK"
print(json.dumps(status, indent=2, sort_keys=True))
raise SystemExit(0)
PY

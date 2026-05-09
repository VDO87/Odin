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

atlas_enabled = os.getenv("ATLAS_ENABLED", "true").lower() == "true"
profile = os.getenv("ATLAS_PROFILE", os.getenv("ATLAS_DEFAULT_PROFILE", "lite")).strip().lower()
lite_enabled = os.getenv("ATLAS_LITE_ENABLED", "true").lower() == "true"
full_enabled = os.getenv("ATLAS_FULL_ENABLED", "true").lower() == "true"

available_agents = {
    "lite": ["market_agent", "technical_agent", "risk_agent", "critic_agent"],
    "full": [
        "market_agent",
        "technical_agent",
        "news_agent",
        "macro_agent",
        "risk_agent",
        "fire_agent",
        "execution_agent",
        "critic_agent",
        "memory_agent",
    ],
}

status = {
    "status": "OK" if atlas_enabled else "WARNING",
    "atlas_enabled": atlas_enabled,
    "atlas_profile": profile if profile in {"lite", "full"} else "lite",
    "atlas_lite_enabled": lite_enabled,
    "atlas_full_enabled": full_enabled,
    "execution_permission": "SHADOW_ONLY",
    "agents_available": available_agents.get(profile if profile in {"lite", "full"} else "lite", []),
    "installs_external_atlas": False,
}
print(json.dumps(status, indent=2, sort_keys=True))
raise SystemExit(0)
PY

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

OFFLINE_OK=0
if [[ "${1:-}" == "--offline-ok" ]]; then
  OFFLINE_OK=1
elif [[ $# -gt 0 ]]; then
  echo "Uso: ./healthcheck.sh [--offline-ok]" >&2
  exit 2
fi

find_python_bin() {
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    echo "$ROOT_DIR/.venv/bin/python"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  return 1
}

PYTHON_BIN="$(find_python_bin || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python não encontrado. Instalar Python 3 ou activar venv." >&2
  exit 127
fi

OUT="$($PYTHON_BIN - "$OFFLINE_OK" <<'PY'
from __future__ import annotations

import json
import sys

from odin_health.healthcheck import OdinHealthcheck

offline_ok = bool(int(sys.argv[1]))
result = OdinHealthcheck(log_root="logs").run()
status = str(result.get("status", "BLOCKED"))
reason = ""

network = result.get("checks", {}).get("network", {})
network_status = str(network.get("status", "UNKNOWN"))

if offline_ok and status == "BLOCKED" and network_status == "CRITICAL":
    status = "WARNING"
    reason = "offline_ok: network/DNS indisponível no ambiente atual"

payload = {
    "status": status,
    "reason": reason or network.get("reason", ""),
    "checks": result.get("checks", {}),
}
print(json.dumps(payload, sort_keys=True))
print(f"FINAL_STATUS={status}")
PY
)"

echo "$OUT"
STATUS="$(echo "$OUT" | awk -F= '/^FINAL_STATUS=/{print $2}' | tail -n1)"

case "$STATUS" in
  OK|WARNING)
    exit 0
    ;;
  CRITICAL|BLOCKED)
    exit 2
    ;;
  *)
    echo "Estado inválido devolvido pelo healthcheck: '$STATUS'" >&2
    exit 3
    ;;
esac

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

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

export ODIN_MODE="${ODIN_MODE:-SHADOW_MT5}"
export ENABLE_REAL_TRADING="false"
export ENABLE_AUTO_EXECUTION="false"
export MT5_ORDER_SEND_ENABLED="false"
export XTB_REAL_ENABLED="false"
export BROKER_ALLOW_REAL_EXECUTION="false"
export ENABLE_XTB_REAL="false"
export ENABLE_MT5_ORDER_SEND="false"

MODE="dashboard"
if [[ $# -gt 0 ]]; then
  case "$1" in
    --smoke-test)
      MODE="smoke"
      ;;
    --dashboard)
      MODE="dashboard"
      ;;
    --healthcheck)
      MODE="healthcheck"
      ;;
    *)
      echo "Uso: ./run_odin.sh [--smoke-test|--dashboard|--healthcheck]" >&2
      exit 2
      ;;
  esac
fi

if [[ "$MODE" == "smoke" ]]; then
  "$PYTHON_BIN" - <<'PY'
import importlib

modules = [
    "odin_control",
    "odin_health",
    "odin_assistant",
    "odin_atlas",
    "odin_brokers",
]
for name in modules:
    importlib.import_module(name)

app_mod = importlib.import_module("apps.dashboard_html.app")
create_app = getattr(app_mod, "create_app", None)
if create_app is None:
    raise RuntimeError("create_app not found in apps.dashboard_html.app")
create_app()
print("ODIN smoke-test OK")
PY
  exit 0
fi

if [[ "$MODE" == "healthcheck" ]]; then
  exec "$ROOT_DIR/healthcheck.sh"
fi

exec "$PYTHON_BIN" -m apps.dashboard_html.app

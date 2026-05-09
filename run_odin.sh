#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -z "${ODIN_HOME:-}" ]]; then
  if [[ "$(basename "$ROOT_DIR")" == "app" ]]; then
    ODIN_HOME="$(cd "$ROOT_DIR/.." && pwd)"
  else
    ODIN_HOME="${ODIN_HOME:-$ROOT_DIR}"
  fi
fi
export ODIN_HOME
if [[ "$(basename "$ROOT_DIR")" == "app" ]]; then
  export ODIN_APP_DIR="${ODIN_APP_DIR:-$ROOT_DIR}"
else
  export ODIN_APP_DIR="${ODIN_APP_DIR:-$ROOT_DIR}"
fi
export ODIN_CONFIG_DIR="${ODIN_CONFIG_DIR:-$ODIN_HOME/config}"
export ODIN_DATA_DIR="${ODIN_DATA_DIR:-$ODIN_HOME/data}"
export ODIN_LOG_DIR="${ODIN_LOG_DIR:-$ODIN_HOME/logs}"
export ODIN_MODELS_DIR="${ODIN_MODELS_DIR:-$ODIN_HOME/models}"
export ODIN_VENDOR_DIR="${ODIN_VENDOR_DIR:-$ODIN_HOME/vendor}"
export ODIN_BACKUP_DIR="${ODIN_BACKUP_DIR:-$ODIN_HOME/backups}"
export ODIN_TMP_DIR="${ODIN_TMP_DIR:-$ODIN_HOME/tmp}"
export ODIN_DASHBOARD_PREVIEW_DIR="${ODIN_DASHBOARD_PREVIEW_DIR:-$ODIN_HOME/dashboard_preview}"
export ODIN_STATE_SNAPSHOT_FILE="${ODIN_STATE_SNAPSHOT_FILE:-$ODIN_DATA_DIR/runtime/odin_state_snapshot.json}"
export ODIN_HEARTBEAT_FILE="${ODIN_HEARTBEAT_FILE:-$ODIN_DATA_DIR/runtime/odin_heartbeat.json}"
export ODIN_EVENTS_FILE="${ODIN_EVENTS_FILE:-$ODIN_DATA_DIR/runtime/odin_events.jsonl}"
export ODIN_SOAK_TEST_OUTPUT_DIR="${ODIN_SOAK_TEST_OUTPUT_DIR:-$ODIN_DATA_DIR/soak_tests}"

mkdir -p "$ODIN_CONFIG_DIR" "$ODIN_DATA_DIR/runtime" "$ODIN_DATA_DIR/soak_tests" "$ODIN_LOG_DIR/system" "$ODIN_DASHBOARD_PREVIEW_DIR" "$ODIN_TMP_DIR"

if [[ -f "$ODIN_CONFIG_DIR/.env" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$ODIN_CONFIG_DIR/.env"; set +a
fi

find_python_bin() {
  if [[ -x "$ODIN_HOME/.venv/bin/python" ]]; then
    echo "$ODIN_HOME/.venv/bin/python"
    return 0
  fi
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
export OPENAI_SUPPORT_ENABLED="false"

MODE="dashboard"
if [[ $# -gt 0 ]]; then
  case "$1" in
    --smoke-test)
      MODE="smoke"
      ;;
    --dashboard)
      MODE="dashboard"
      ;;
    --dashboard-preview)
      MODE="dashboard-preview"
      ;;
    --dashboard-qa)
      MODE="dashboard-qa"
      ;;
    --tui)
      MODE="tui"
      ;;
    --tui-demo)
      MODE="tui-demo"
      ;;
    --tui-once)
      MODE="tui-once"
      ;;
    --tui-smoke-test)
      MODE="tui-smoke-test"
      ;;
    --healthcheck)
      MODE="healthcheck"
      ;;
    --runtime)
      MODE="runtime"
      ;;
    --run-once)
      MODE="run-once"
      ;;
    --runtime-smoke-test)
      MODE="runtime-smoke"
      ;;
    --snapshot)
      MODE="snapshot"
      ;;
    --runtime-validate)
      MODE="runtime-validate"
      ;;
    --soak-test)
      MODE="soak-test"
      ;;
    --soak-test-mini)
      MODE="soak-test-mini"
      ;;
    --soak-report)
      MODE="soak-report"
      ;;
    *)
      echo "Uso: ./run_odin.sh [--smoke-test|--dashboard|--dashboard-preview|--dashboard-qa|--tui|--tui-demo|--tui-once|--tui-smoke-test|--healthcheck|--runtime|--run-once|--runtime-smoke-test|--snapshot|--runtime-validate|--soak-test|--soak-test-mini|--soak-report]" >&2
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

if [[ "$MODE" == "runtime-smoke" ]]; then
  "$PYTHON_BIN" - <<'PY'
from odin_control.system_controller import SystemController

controller = SystemController(log_root="logs")
status = controller.execute("RUNTIME_STATUS", actor="run_odin", role="system")
once = controller.execute("RUNTIME_RUN_ONCE", actor="run_odin", role="system")
snap = controller.execute("RUNTIME_SNAPSHOT", actor="run_odin", role="system")
assert status["accepted"] is True
assert "runtime" in status["data"]
assert "runtime" in once["data"]
assert "snapshot" in snap["data"]
print("ODIN runtime smoke-test OK")
PY
  exit 0
fi

if [[ "$MODE" == "dashboard-preview" ]]; then
  exec "$PYTHON_BIN" -m apps.dashboard_html.app --export-preview
fi

if [[ "$MODE" == "dashboard-qa" ]]; then
  exec "$PYTHON_BIN" -m apps.dashboard_html.app --dashboard-qa
fi

if [[ "$MODE" == "tui-smoke-test" ]]; then
  exec "$PYTHON_BIN" -m apps.dashboard_tui.app --smoke-test
fi

if [[ "$MODE" == "tui-once" ]]; then
  exec "$PYTHON_BIN" -m apps.dashboard_tui.app --once
fi

if [[ "$MODE" == "tui-demo" ]]; then
  exec "$PYTHON_BIN" -m apps.dashboard_tui.app --once --demo
fi

if [[ "$MODE" == "tui" ]]; then
  exec "$PYTHON_BIN" -m apps.dashboard_tui.app
fi

if [[ "$MODE" == "runtime-validate" ]]; then
  exec "$PYTHON_BIN" - <<'PY'
from odin_core.runtime_validator import log_runtime_validation, validate_runtime_artifacts
import json
import sys

result = validate_runtime_artifacts()
log_runtime_validation(result)
print(json.dumps(result, indent=2, sort_keys=True))
sys.exit(0 if result.get("status") in {"PASS", "WARNING"} else 1)
PY
fi

if [[ "$MODE" == "soak-test" ]]; then
  exec "$PYTHON_BIN" -m tools.odin_soak_test --report docs/reports/ODIN_RC1_5_SOAK_TEST_RESULT.md
fi

if [[ "$MODE" == "soak-test-mini" ]]; then
  exec "$PYTHON_BIN" -m tools.odin_soak_test --mini --report docs/reports/ODIN_RC1_5_SOAK_TEST_RESULT.md
fi

if [[ "$MODE" == "soak-report" ]]; then
  exec "$PYTHON_BIN" - <<'PY'
from pathlib import Path
import json

path = Path("data/runtime/soak_tests/latest_soak_result.json")
if not path.exists():
    print(json.dumps({"status": "missing", "message": "Soak report não encontrado"}, indent=2))
    raise SystemExit(1)
print(path.read_text(encoding="utf-8"))
PY
fi

if [[ "$MODE" == "run-once" ]]; then
  exec "$PYTHON_BIN" - <<'PY'
from odin_control.system_controller import SystemController
import json

controller = SystemController(log_root="logs")
result = controller.execute("RUNTIME_RUN_ONCE", actor="run_odin", role="system")
print(json.dumps(result, indent=2, sort_keys=True))
PY
fi

if [[ "$MODE" == "snapshot" ]]; then
  exec "$PYTHON_BIN" - <<'PY'
from odin_control.system_controller import SystemController
import json

controller = SystemController(log_root="logs")
result = controller.execute("RUNTIME_SNAPSHOT", actor="run_odin", role="system")
print(json.dumps(result, indent=2, sort_keys=True))
PY
fi

if [[ "$MODE" == "runtime" ]]; then
  exec "$PYTHON_BIN" - <<'PY'
from odin_control.system_controller import SystemController

controller = SystemController(log_root="logs")
controller.execute("RUNTIME_START", actor="run_odin", role="system")
controller.runtime.run_loop()
PY
fi

if [[ "$MODE" == "dashboard" ]]; then
  echo "Dashboard disponível em http://127.0.0.1:8000"
  exec "$PYTHON_BIN" -m apps.dashboard_html.app --host 127.0.0.1 --port 8000
fi

exec "$PYTHON_BIN" -m apps.dashboard_html.app

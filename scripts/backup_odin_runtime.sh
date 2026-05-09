#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ODIN_HOME="${HOME}/ODIN_RUNTIME"
INCLUDE_LOGS=0
INCLUDE_MODELS=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --odin-home)
      ODIN_HOME="$2"
      shift 2
      ;;
    --include-logs)
      INCLUDE_LOGS=1
      shift
      ;;
    --include-models)
      INCLUDE_MODELS=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "Uso: $0 [--odin-home PATH] [--include-logs] [--include-models] [--dry-run]" >&2
      exit 2
      ;;
  esac
done

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
fi
if [[ -z "${PYTHON_BIN:-}" ]]; then
  echo "Python não encontrado." >&2
  exit 127
fi

"$PYTHON_BIN" - "$ODIN_HOME" "$INCLUDE_LOGS" "$INCLUDE_MODELS" "$DRY_RUN" <<'PY'
from pathlib import Path
import sys

from odin_deploy.backup import create_runtime_backup
from odin_deploy.paths import resolve_deploy_paths

odin_home = sys.argv[1]
include_logs = bool(int(sys.argv[2]))
include_models = bool(int(sys.argv[3]))
dry_run = bool(int(sys.argv[4]))
paths = resolve_deploy_paths(odin_home)
backup_file = create_runtime_backup(
    paths,
    include_logs=include_logs,
    include_models=include_models,
    dry_run=dry_run,
)
print({"status": "OK", "backup_file": str(Path(backup_file))})
PY

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ODIN_HOME="${HOME}/ODIN_RUNTIME"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --odin-home)
      ODIN_HOME="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "Uso: $0 [--odin-home PATH] [--dry-run]" >&2
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

export ODIN_HOME
if [[ "$DRY_RUN" -eq 1 ]]; then
  export ODIN_DEPLOY_DRY_RUN=true
else
  export ODIN_DEPLOY_DRY_RUN=false
fi

"$PYTHON_BIN" -m odin_deploy.validator

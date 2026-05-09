#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ODIN_HOME="${HOME}/ODIN_RUNTIME"
DRY_RUN=0
BACKUP_FIRST=0
SKIP_DEPS=0

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
    --backup-first)
      BACKUP_FIRST=1
      shift
      ;;
    --skip-deps)
      SKIP_DEPS=1
      shift
      ;;
    *)
      echo "Uso: $0 [--odin-home PATH] [--dry-run] [--backup-first] [--skip-deps]" >&2
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

mkdir -p "$ROOT_DIR/logs/system"
LOG_FILE="$ROOT_DIR/logs/system/update_runtime.log"
printf '[%s] update_odin_runtime start odin_home=%s dry_run=%s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$ODIN_HOME" "$DRY_RUN" | tee -a "$LOG_FILE"

ARGS=(--mode update --odin-home "$ODIN_HOME")
[[ "$DRY_RUN" -eq 1 ]] && ARGS+=(--dry-run)
[[ "$BACKUP_FIRST" -eq 1 ]] && ARGS+=(--backup-first)
[[ "$SKIP_DEPS" -eq 1 ]] && ARGS+=(--skip-deps)
"$PYTHON_BIN" -m odin_deploy.installer "${ARGS[@]}" | tee -a "$LOG_FILE"

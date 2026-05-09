#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ODIN_HOME="${HOME}/ODIN_RUNTIME"
BACKUP_FILE=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --odin-home)
      ODIN_HOME="$2"
      shift 2
      ;;
    --backup-file)
      BACKUP_FILE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "Uso: $0 --backup-file FILE [--odin-home PATH] [--dry-run]" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$BACKUP_FILE" ]]; then
  echo "backup-file é obrigatório." >&2
  exit 2
fi

PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
fi
if [[ -z "${PYTHON_BIN:-}" ]]; then
  echo "Python não encontrado." >&2
  exit 127
fi

"$PYTHON_BIN" - "$ODIN_HOME" "$BACKUP_FILE" "$DRY_RUN" <<'PY'
from pathlib import Path
import json
import sys

from odin_deploy.backup import restore_runtime_backup
from odin_deploy.paths import resolve_deploy_paths

odin_home = sys.argv[1]
backup_file = Path(sys.argv[2])
dry_run = bool(int(sys.argv[3]))
paths = resolve_deploy_paths(odin_home)
result = restore_runtime_backup(paths, backup_file, dry_run=dry_run)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result.get("status") == "OK" else 1)
PY

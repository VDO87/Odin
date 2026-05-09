#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ODIN_HOME="${HOME}/ODIN_RUNTIME"
DRY_RUN=0
OFFLINE=0
SKIP_VENV=0
SKIP_DEPS=0
NO_SYSTEMD=0
WITH_SYSTEMD=0
COPY_CURRENT_APP=1

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
    --offline)
      OFFLINE=1
      shift
      ;;
    --skip-venv)
      SKIP_VENV=1
      shift
      ;;
    --skip-deps)
      SKIP_DEPS=1
      shift
      ;;
    --no-systemd)
      NO_SYSTEMD=1
      shift
      ;;
    --with-systemd)
      WITH_SYSTEMD=1
      shift
      ;;
    --copy-current-app)
      COPY_CURRENT_APP=1
      shift
      ;;
    *)
      echo "Uso: $0 [--odin-home PATH] [--dry-run] [--offline] [--skip-venv] [--skip-deps] [--no-systemd] [--with-systemd] [--copy-current-app]" >&2
      exit 2
      ;;
  esac
done

PYTHON_BIN=""
if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  echo "Python não encontrado. Instalar Python 3 ou activar venv." >&2
  exit 127
fi

mkdir -p "$ROOT_DIR/logs/system"
LOG_FILE="$ROOT_DIR/logs/system/install_runtime.log"
printf '[%s] install_odin_runtime start odin_home=%s dry_run=%s offline=%s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$ODIN_HOME" "$DRY_RUN" "$OFFLINE" | tee -a "$LOG_FILE"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "install_odin_runtime dry-run active" | tee -a "$LOG_FILE"
fi

export ODIN_HOME
ARGS=(--mode install --odin-home "$ODIN_HOME")
[[ "$DRY_RUN" -eq 1 ]] && ARGS+=(--dry-run)
[[ "$OFFLINE" -eq 1 ]] && ARGS+=(--offline)
[[ "$SKIP_VENV" -eq 1 ]] && ARGS+=(--skip-venv)
[[ "$SKIP_DEPS" -eq 1 ]] && ARGS+=(--skip-deps)
[[ "$NO_SYSTEMD" -eq 1 ]] && ARGS+=(--no-systemd)
[[ "$WITH_SYSTEMD" -eq 1 ]] && ARGS+=(--with-systemd)
[[ "$COPY_CURRENT_APP" -eq 1 ]] && ARGS+=(--copy-current-app)

"$PYTHON_BIN" -m odin_deploy.installer "${ARGS[@]}" | tee -a "$LOG_FILE"

if [[ "$DRY_RUN" -eq 0 ]]; then
  printf '\nInstalação concluída.\n'
  printf 'Próximos passos:\n'
  printf '1) %s/app/run_odin.sh --dashboard-preview\n' "$ODIN_HOME"
  printf '2) %s/app/run_odin.sh --dashboard-qa\n' "$ODIN_HOME"
  printf '3) %s/app/scripts/validate_odin_runtime.sh --odin-home %s\n' "$ODIN_HOME" "$ODIN_HOME"
fi

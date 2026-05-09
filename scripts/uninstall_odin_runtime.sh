#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ODIN_HOME="${HOME}/ODIN_RUNTIME"
DRY_RUN=0
KEEP_DATA=1
KEEP_LOGS=1
KEEP_CONFIG=1
REMOVE_SYSTEMD=0

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
    --keep-data)
      KEEP_DATA=1
      shift
      ;;
    --keep-logs)
      KEEP_LOGS=1
      shift
      ;;
    --keep-config)
      KEEP_CONFIG=1
      shift
      ;;
    --remove-systemd)
      REMOVE_SYSTEMD=1
      shift
      ;;
    *)
      echo "Uso: $0 [--odin-home PATH] [--dry-run] [--keep-data] [--keep-logs] [--keep-config] [--remove-systemd]" >&2
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

if [[ "$DRY_RUN" -eq 0 ]]; then
  read -r -p "Confirmar uninstall em ${ODIN_HOME}? [yes/no] " CONFIRM
  if [[ "$CONFIRM" != "yes" ]]; then
    echo "Uninstall cancelado."
    exit 1
  fi
fi

ARGS=(--mode uninstall --odin-home "$ODIN_HOME")
[[ "$DRY_RUN" -eq 1 ]] && ARGS+=(--dry-run)
[[ "$KEEP_DATA" -eq 1 ]] && ARGS+=(--keep-data)
[[ "$KEEP_LOGS" -eq 1 ]] && ARGS+=(--keep-logs)
[[ "$KEEP_CONFIG" -eq 1 ]] && ARGS+=(--keep-config)
[[ "$REMOVE_SYSTEMD" -eq 1 ]] && ARGS+=(--remove-systemd)
"$PYTHON_BIN" -m odin_deploy.installer "${ARGS[@]}"

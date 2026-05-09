#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'HELP'
Usage: ODIN_HOME=/path/to/odin-install scripts/odin_purge.sh [options]

Options:
  --dry-run          Show actions without changing files/processes
  --remove-config    Also remove $ODIN_HOME/config/odin.local.toml
  --remove-install   Remove the whole $ODIN_HOME folder
  --help             Show this help

Safety:
  - Requires ODIN_HOME to be set
  - Refuses empty/"/"/repository-root targets
  - Requires explicit confirmation token: PURGE_ODIN
HELP
}

log() {
  printf '[odin-purge] %s\n' "$1"
}

fail() {
  printf '[odin-purge][error] %s\n' "$1" >&2
  exit 1
}

run_cmd() {
  if [[ "$dry_run" -eq 1 ]]; then
    printf '[dry-run]'
    printf ' %q' "$@"
    printf '\n'
    return 0
  fi
  "$@"
}

dry_run=0
remove_config=0
remove_install=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=1
      ;;
    --remove-config)
      remove_config=1
      ;;
    --remove-install)
      remove_install=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
  shift
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "${ODIN_HOME:-}" ]]; then
  fail "ODIN_HOME is required"
fi

odin_home="$(python3 -c 'import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))' "$ODIN_HOME")"

if [[ -z "$odin_home" || "$odin_home" == "/" ]]; then
  fail "Refusing unsafe ODIN_HOME: '$odin_home'"
fi

if [[ "$odin_home" == "$repo_root" ]]; then
  fail "Refusing repository root target: '$odin_home'"
fi

log "Target installation: $odin_home"
if [[ "$remove_install" -eq 1 ]]; then
  log "Mode: full install removal (--remove-install)"
else
  log "Mode: runtime purge"
fi
if [[ "$remove_config" -eq 1 ]]; then
  log "Config removal enabled: $odin_home/config/odin.local.toml"
fi
if [[ "$dry_run" -eq 1 ]]; then
  log "Dry-run enabled: no changes will be applied"
fi

printf "Type PURGE_ODIN to continue: "
read -r confirmation
if [[ "$confirmation" != "PURGE_ODIN" ]]; then
  fail "Confirmation token mismatch"
fi

stop_processes() {
  local patterns=(
    "$odin_home/bin/start_odin.sh"
    "$odin_home/bin/start_operator_console.sh"
    "$odin_home/config/odin.local.toml"
    "apps.core_daemon"
    "apps.operator_console"
  )
  for pattern in "${patterns[@]}"; do
    if [[ "$dry_run" -eq 1 ]]; then
      printf '[dry-run] pkill -f %q || true\n' "$pattern"
    else
      pkill -f "$pattern" 2>/dev/null || true
    fi
  done
}

purge_dir_keep_gitkeep() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    log "Skipping missing directory: $dir"
    return 0
  fi
  if [[ "$dry_run" -eq 1 ]]; then
    printf '[dry-run] find %q -mindepth 1 ! -name .gitkeep -delete\n' "$dir"
    return 0
  fi
  find "$dir" -mindepth 1 ! -name ".gitkeep" -delete
}

log "Stopping related processes (best effort)..."
stop_processes

if [[ "$remove_install" -eq 1 ]]; then
  if [[ ! -d "$odin_home" ]]; then
    log "Install folder does not exist: $odin_home"
    exit 0
  fi
  log "Removing full install directory: $odin_home"
  run_cmd rm -rf "$odin_home"
  log "Purge complete."
  exit 0
fi

purge_dir_keep_gitkeep "$odin_home/runtime/state"
purge_dir_keep_gitkeep "$odin_home/runtime/logs"
purge_dir_keep_gitkeep "$odin_home/runtime/backups"
purge_dir_keep_gitkeep "$odin_home/runtime/memory"

if [[ "$remove_config" -eq 1 ]]; then
  config_path="$odin_home/config/odin.local.toml"
  if [[ -f "$config_path" ]]; then
    log "Removing config file: $config_path"
    run_cmd rm -f "$config_path"
  else
    log "Config file not present: $config_path"
  fi
fi

log "Purge complete."

#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
odin_home="${ODIN_HOME:-$root_dir}"
cd "$odin_home"

python_bin="${ODIN_PYTHON_BIN:-$odin_home/.venv/bin/python}"
config_path="${ODIN_CONFIG_PATH:-$odin_home/config/odin.local.toml}"
poll_interval_ms="${ODIN_POLL_INTERVAL_MS:-1000}"
status_file="${ODIN_STATUS_FILE:-$odin_home/runtime/state/core_public_view.json}"
lifecycle_log="${ODIN_LIFECYCLE_LOG:-$odin_home/runtime/logs/core-daemon-lifecycle.jsonl}"
enable_heartbeat_supervision="${ODIN_ENABLE_HEARTBEAT_SUPERVISION:-0}"

if [[ ! -x "$python_bin" ]]; then
  echo "Python runtime not found at $python_bin"
  echo "Run ./INSTALL_ODIN.sh first to create .venv."
  exit 1
fi

if [[ ! -f "$config_path" ]]; then
  echo "Config file not found at $config_path"
  echo "Expected config/odin.local.toml. Run ./INSTALL_ODIN.sh first if needed."
  exit 1
fi

mkdir -p "$odin_home/runtime/state" "$odin_home/runtime/logs" "$odin_home/runtime/backups" "$odin_home/runtime/memory"
export PYTHONUNBUFFERED=1

args=(
  -m
  apps.core_daemon
  --config
  "$config_path"
  --poll-interval-ms
  "$poll_interval_ms"
  --status-file
  "$status_file"
  --lifecycle-log
  "$lifecycle_log"
)

if [[ "$enable_heartbeat_supervision" == "1" ]]; then
  args+=(--enable-heartbeat-supervision)
fi

exec "$python_bin" "${args[@]}" "$@"

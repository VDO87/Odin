#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
service_name="odin-core.service"
service_template="$root_dir/systemd/odin-core.service.template"
service_target="/etc/systemd/system/${service_name}"
enable_service=1
start_service=0

usage() {
  cat <<'EOF'
Usage: scripts/install_systemd_service.sh [options]

Options:
  --skip-enable   Install the unit file but do not enable it
  --start         Start the service after installation
  --help          Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-enable)
      enable_service=0
      ;;
    --start)
      start_service=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
  shift
done

log() {
  printf "[odin-systemd] %s\n" "$1"
}

run_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "This action needs root privileges. Please run as root or install sudo."
    exit 1
  fi
}

escape_sed() {
  printf '%s' "$1" | sed 's/[\/&]/\\&/g'
}

if [[ ! -f "$service_template" ]]; then
  echo "Missing service template: $service_template"
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found. This installer targets systemd-based Ubuntu Server."
  exit 1
fi

odin_user="${ODIN_SYSTEMD_USER:-${SUDO_USER:-$(id -un)}}"
odin_group="${ODIN_SYSTEMD_GROUP:-$(id -gn "$odin_user")}"
odin_config="${ODIN_CONFIG_PATH:-$root_dir/config/odin.local.toml}"
odin_status_file="${ODIN_STATUS_FILE:-$root_dir/runtime/state/core_public_view.json}"

tmp_unit="$(mktemp)"
sed \
  -e "s/__ODIN_ROOT__/$(escape_sed "$root_dir")/g" \
  -e "s/__ODIN_USER__/$(escape_sed "$odin_user")/g" \
  -e "s/__ODIN_GROUP__/$(escape_sed "$odin_group")/g" \
  -e "s/__ODIN_CONFIG__/$(escape_sed "$odin_config")/g" \
  -e "s/__ODIN_STATUS_FILE__/$(escape_sed "$odin_status_file")/g" \
  "$service_template" > "$tmp_unit"

run_root install -m 0644 "$tmp_unit" "$service_target"
rm -f "$tmp_unit"

run_root systemctl daemon-reload

if [[ "$enable_service" -eq 1 ]]; then
  run_root systemctl enable "$service_name"
  log "Enabled $service_name"
else
  log "Installed $service_name without enabling it"
fi

if [[ "$start_service" -eq 1 ]]; then
  run_root systemctl restart "$service_name"
  log "Started $service_name"
fi

echo "Installed unit file: $service_target"
echo "Service management:"
echo "  sudo systemctl status $service_name"
echo "  sudo systemctl restart $service_name"

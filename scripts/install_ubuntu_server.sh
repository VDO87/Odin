#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"

with_memory=1
skip_apt=0
skip_systemd=0

usage() {
  cat <<'EOF'
Usage: ./INSTALL_ODIN.sh [options]

Options:
  --with-memory       Install optional MemPalace support (default)
  --without-memory    Skip MemPalace support
  --skip-apt          Skip apt package installation
  --skip-systemd      Skip systemd service installation
  --help              Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-memory)
      with_memory=1
      ;;
    --without-memory)
      with_memory=0
      ;;
    --skip-apt)
      skip_apt=1
      ;;
    --skip-systemd)
      skip_systemd=1
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
  printf "[odin-install] %s\n" "$1"
}

run_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "This installer needs root privileges for apt. Please run as root or install sudo."
    exit 1
  fi
}

ensure_ubuntu() {
  if [[ ! -f /etc/os-release ]]; then
    echo "Unsupported system: /etc/os-release not found."
    exit 1
  fi

  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" != "ubuntu" ]]; then
    echo "This installer targets Ubuntu Server. Detected: ${ID:-unknown}"
    exit 1
  fi
}

ensure_runtime_layout() {
  install -d \
    "$root_dir/runtime/logs" \
    "$root_dir/runtime/state" \
    "$root_dir/runtime/backups" \
    "$root_dir/runtime/memory" \
    "$root_dir/config/examples" \
    "$root_dir/scripts" \
    "$root_dir/tools" \
    "$root_dir/assets" \
    "$root_dir/.github/workflows"
}

ensure_local_config() {
  if [[ ! -f "$root_dir/config/odin.local.toml" ]]; then
    cp "$root_dir/config/examples/odin.example.toml" "$root_dir/config/odin.local.toml"
    log "Created config/odin.local.toml from example."
  else
    log "config/odin.local.toml already exists. Keeping current file."
  fi

  if [[ "$with_memory" -eq 1 ]]; then
    sed -i 's/^enabled = false$/enabled = true/' "$root_dir/config/odin.local.toml" || true
  else
    sed -i 's/^enabled = true$/enabled = false/' "$root_dir/config/odin.local.toml" || true
  fi
}

install_system_packages() {
  if [[ "$skip_apt" -eq 1 ]]; then
    log "Skipping apt package installation."
    return 0
  fi

  log "Installing Ubuntu system packages..."
  run_root apt-get update
  run_root apt-get install -y \
    bash \
    ca-certificates \
    curl \
    git \
    sqlite3 \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential
}

bootstrap_python_env() {
  log "Checking prerequisites..."
  if [[ "$with_memory" -eq 1 ]]; then
    "$root_dir/scripts/check_prereqs.sh" --with-memory
    log "Bootstrapping Python environment with optional advisory memory support..."
    "$root_dir/scripts/bootstrap_dev.sh" --with-memory
  else
    "$root_dir/scripts/check_prereqs.sh"
    log "Bootstrapping Python environment without advisory memory..."
    "$root_dir/scripts/bootstrap_dev.sh"
  fi
}

install_systemd_unit() {
  if [[ "$skip_systemd" -eq 1 ]]; then
    log "Skipping systemd service installation."
    return 0
  fi

  if ! command -v systemctl >/dev/null 2>&1; then
    log "systemctl not found. Skipping systemd service installation."
    return 0
  fi

  log "Installing odin-core.service for systemd..."
  "$root_dir/scripts/install_systemd_service.sh"
}

print_summary() {
  log "Installation complete."
  echo
  echo "Installed project root: $root_dir"
  echo "Local config:            $root_dir/config/odin.local.toml"
  echo "Virtualenv:              $root_dir/.venv"
  echo "Runtime state dir:       $root_dir/runtime/state"
  echo "Runtime log dir:         $root_dir/runtime/logs"
  echo "Runtime memory dir:      $root_dir/runtime/memory"
  if [[ "$skip_systemd" -eq 0 ]]; then
    echo "Systemd service:         odin-core.service installed"
  else
    echo "Systemd service:         skipped"
  fi
  if [[ "$with_memory" -eq 1 ]]; then
    echo "Advisory memory:         enabled in environment"
  else
    echo "Advisory memory:         not installed"
  fi
  echo
  echo "Next step:"
  echo "  ./start_odin.sh"
  if [[ "$skip_systemd" -eq 0 ]]; then
    echo "  sudo systemctl start odin-core.service"
  fi
}

ensure_ubuntu
install_system_packages
ensure_runtime_layout
ensure_local_config
chmod +x "$root_dir/INSTALL_ODIN.sh" "$root_dir/start_odin.sh" "$root_dir/scripts/"*.sh
bootstrap_python_env
install_systemd_unit
print_summary

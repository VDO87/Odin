#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$root_dir"

profile="lite"
memory_requested="auto"
dry_run=0
skip_apt=0
skip_systemd=0
config_created=0
install_mode="isolated"
install_root="${ODIN_INSTALL_ROOT:-$HOME/odin-runtime}"

usage() {
  cat <<'HELP'
Usage: ./INSTALL_ODIN.sh [options]

Options:
  --profile <lite|standard|full>  Execution profile to prepare (default: lite)
  --with-memory                   Enable auxiliary memory support (full profile only)
  --without-memory                Disable auxiliary memory support
  --dry-run                       Show actions and validations without changing the system
  --skip-apt                      Skip apt package installation
  --skip-systemd                  Skip systemd service installation
  --install-root <path>           Install runtime/config/venv in an isolated folder
  --in-place                      Keep legacy in-repo install layout (config/.venv/runtime)
  --help                          Show this help
HELP
}

log() {
  printf "[odin-install] %s\n" "$1"
}

fail() {
  printf "[odin-install][error] %s\n" "$1" >&2
  exit 1
}

run_cmd() {
  if [[ "$dry_run" -eq 1 ]]; then
    printf "[dry-run]"
    printf " %q" "$@"
    printf "\n"
    return 0
  fi
  "$@"
}

run_root() {
  if [[ "$dry_run" -eq 1 ]]; then
    printf "[dry-run][root]"
    printf " %q" "$@"
    printf "\n"
    return 0
  fi
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    fail "This installer needs root privileges for apt. Run as root or install sudo."
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      shift
      [[ $# -gt 0 ]] || fail "--profile requires a value"
      profile="$1"
      ;;
    --with-memory)
      memory_requested="with"
      ;;
    --without-memory)
      memory_requested="without"
      ;;
    --dry-run)
      dry_run=1
      ;;
    --skip-apt)
      skip_apt=1
      ;;
    --skip-systemd)
      skip_systemd=1
      ;;
    --install-root)
      shift
      [[ $# -gt 0 ]] || fail "--install-root requires a value"
      install_mode="isolated"
      install_root="$1"
      ;;
    --in-place)
      install_mode="inplace"
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

case "$profile" in
  lite|standard|full)
    ;;
  *)
    fail "Unsupported profile: $profile"
    ;;
esac

if [[ "$memory_requested" == "auto" ]]; then
  if [[ "$profile" == "full" ]]; then
    with_memory=1
  else
    with_memory=0
  fi
elif [[ "$memory_requested" == "with" ]]; then
  with_memory=1
else
  with_memory=0
fi

if [[ "$with_memory" -eq 1 && "$profile" != "full" ]]; then
  fail "Auxiliary memory is only supported by the full profile."
fi

if [[ "$install_mode" == "inplace" ]]; then
  install_root="$root_dir"
fi

install_root="$(python3 -c 'import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))' "$install_root")"

config_example_for_profile() {
  case "$1" in
    lite)
      printf "%s\n" "$root_dir/config/examples/odin.example.toml"
      ;;
    standard)
      printf "%s\n" "$root_dir/config/examples/odin.standard.example.toml"
      ;;
    full)
      printf "%s\n" "$root_dir/config/examples/odin.full.example.toml"
      ;;
  esac
}

config_example="$(config_example_for_profile "$profile")"
config_path="$install_root/config/odin.local.toml"
venv_dir="$install_root/.venv"
runtime_root="$install_root/runtime"
manifest_path="$install_root/install-manifest.json"

validate_repo_layout() {
  [[ -f "$config_example" ]] || fail "Missing profile example: $config_example"
  [[ -f "$root_dir/start_odin.sh" ]] || fail "Missing start_odin.sh"
  [[ -f "$root_dir/scripts/check_prereqs.sh" ]] || fail "Missing scripts/check_prereqs.sh"
  [[ -f "$root_dir/scripts/bootstrap_dev.sh" ]] || fail "Missing scripts/bootstrap_dev.sh"
  [[ -f "$root_dir/scripts/install_systemd_service.sh" ]] || fail "Missing scripts/install_systemd_service.sh"
}

ensure_ubuntu() {
  if [[ "${ODIN_INSTALL_SKIP_OS_CHECK:-0}" == "1" ]]; then
    log "Skipping Ubuntu OS validation because ODIN_INSTALL_SKIP_OS_CHECK=1."
    return 0
  fi
  if [[ "$dry_run" -eq 1 ]]; then
    log "Dry-run: skipping Ubuntu OS validation."
    return 0
  fi
  if [[ ! -f /etc/os-release ]]; then
    fail "Unsupported system: /etc/os-release not found."
  fi

  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" != "ubuntu" ]]; then
    fail "This installer targets Ubuntu Server. Detected: ${ID:-unknown}"
  fi
}

ensure_runtime_layout() {
  run_cmd install -d \
    "$runtime_root/logs" \
    "$runtime_root/state" \
    "$runtime_root/backups"
  if [[ "$with_memory" -eq 1 ]]; then
    run_cmd install -d "$runtime_root/memory"
  fi
}

ensure_local_config() {
  run_cmd install -d "$install_root/config"
  if [[ ! -f "$config_path" ]]; then
    run_cmd cp "$config_example" "$config_path"
    config_created=1
    log "Created $config_path from $(basename "$config_example")."
  else
    log "$config_path already exists. Keeping current file."
  fi

  if [[ "$config_created" -eq 1 ]]; then
    if [[ "$with_memory" -eq 1 ]]; then
      run_cmd sed -i 's/^enabled = false$/enabled = true/' "$config_path"
    else
      run_cmd sed -i 's/^enabled = true$/enabled = false/' "$config_path"
    fi
    run_cmd sed -i "s|^state_dir = \".*\"|state_dir = \"$runtime_root/state\"|" "$config_path"
    run_cmd sed -i "s|^log_dir = \".*\"|log_dir = \"$runtime_root/logs\"|" "$config_path"
    run_cmd sed -i "s|^backup_dir = \".*\"|backup_dir = \"$runtime_root/backups\"|" "$config_path"
    run_cmd sed -i "s|^memory_dir = \".*\"|memory_dir = \"$runtime_root/memory\"|" "$config_path"
    run_cmd sed -i "s|^audit_export_dir = \".*\"|audit_export_dir = \"$runtime_root/logs/real-audit\"|" "$config_path"
    run_cmd sed -i "s|^palace_dir = \".*\"|palace_dir = \"$runtime_root/memory/mempalace\"|" "$config_path"
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
  if [[ "$dry_run" -eq 1 ]]; then
    log "Dry-run: skipping Python bootstrap."
    return 0
  fi

  log "Checking prerequisites..."
  if [[ "$with_memory" -eq 1 ]]; then
    "$root_dir/scripts/check_prereqs.sh" --with-memory
    log "Bootstrapping Python environment with auxiliary memory support..."
    ODIN_VENV_DIR="$venv_dir" "$root_dir/scripts/bootstrap_dev.sh" --with-memory
  else
    "$root_dir/scripts/check_prereqs.sh"
    log "Bootstrapping Python environment without auxiliary memory..."
    ODIN_VENV_DIR="$venv_dir" "$root_dir/scripts/bootstrap_dev.sh"
  fi

  log "Validating resulting Odin configuration..."
  "$venv_dir/bin/python" -m apps.validate_config \
    --config "$config_path" \
    --expect-profile "$profile"
}

install_systemd_unit() {
  if [[ "$skip_systemd" -eq 1 ]]; then
    log "Skipping systemd service installation."
    return 0
  fi

  if [[ "$install_mode" == "isolated" ]]; then
    log "Skipping systemd service installation in isolated mode (requires custom unit path wiring)."
    return 0
  fi

  if [[ "$dry_run" -eq 1 ]]; then
    log "Dry-run: skipping systemd service installation."
    return 0
  fi

  if ! command -v systemctl >/dev/null 2>&1; then
    log "systemctl not found. Skipping systemd service installation."
    return 0
  fi

  log "Installing odin-core.service for systemd..."
  "$root_dir/scripts/install_systemd_service.sh"
}

write_install_manifest() {
  if [[ "$dry_run" -eq 1 ]]; then
    log "Dry-run: skipping install manifest."
    return 0
  fi
  run_cmd install -d "$install_root/bin"
  python3 - <<'PY' "$manifest_path" "$install_root" "$root_dir" "$profile" "$with_memory" "$config_path" "$venv_dir"
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

manifest_path = Path(sys.argv[1])
install_root = Path(sys.argv[2])
source_root = Path(sys.argv[3])
profile = sys.argv[4]
with_memory = sys.argv[5] == "1"
config_path = Path(sys.argv[6])
venv_dir = Path(sys.argv[7])

payload = {
    "installed_at_utc": datetime.now(timezone.utc).isoformat(),
    "install_root": str(install_root),
    "source_root": str(source_root),
    "profile": profile,
    "with_memory": with_memory,
    "config_path": str(config_path),
    "venv_dir": str(venv_dir),
    "runtime_dirs": {
        "state": str(install_root / "runtime" / "state"),
        "logs": str(install_root / "runtime" / "logs"),
        "backups": str(install_root / "runtime" / "backups"),
        "memory": str(install_root / "runtime" / "memory"),
    },
}
manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
PY
  cat >"$install_root/bin/start_odin.sh" <<LAUNCH1
#!/usr/bin/env bash
set -euo pipefail
exec "$venv_dir/bin/python" -m apps.core_daemon --config "$config_path" "\$@"
LAUNCH1
  cat >"$install_root/bin/start_operator_console.sh" <<LAUNCH2
#!/usr/bin/env bash
set -euo pipefail
exec "$venv_dir/bin/python" -m apps.operator_console --config "$config_path" "\$@"
LAUNCH2
  run_cmd chmod +x "$install_root/bin/start_odin.sh" "$install_root/bin/start_operator_console.sh"
}

print_summary() {
  if [[ "$dry_run" -eq 1 ]]; then
    log "Dry-run complete. No changes were made."
  else
    log "Installation complete."
  fi
  echo
  echo "Profile:                 $profile"
  echo "Install mode:            $install_mode"
  echo "Install root:            $install_root"
  echo "Local config:            $config_path"
  echo "Runtime state dir:       $runtime_root/state"
  echo "Runtime log dir:         $runtime_root/logs"
  echo "Python venv:             $venv_dir"
  echo "Auxiliary memory:        $([[ "$with_memory" -eq 1 ]] && echo enabled || echo disabled)"
  echo "Systemd service:         $([[ "$skip_systemd" -eq 0 && "$dry_run" -eq 0 && "$install_mode" == "inplace" ]] && echo odin-core.service || echo skipped)"
  echo
  if [[ "$dry_run" -eq 1 ]]; then
    echo "Planned next step:"
  else
    echo "Next step:"
  fi
  if [[ "$install_mode" == "isolated" ]]; then
    echo "  $install_root/bin/start_odin.sh"
    echo "  $install_root/bin/start_operator_console.sh"
    echo "  cat $manifest_path"
  else
    echo "  ./start_odin.sh"
    if [[ "$skip_systemd" -eq 0 && "$dry_run" -eq 0 ]]; then
      echo "  sudo systemctl start odin-core.service"
    fi
  fi
}

validate_repo_layout
ensure_ubuntu
ensure_runtime_layout
ensure_local_config
run_cmd chmod +x "$root_dir/INSTALL_ODIN.sh" "$root_dir/start_odin.sh" "$root_dir/scripts/"*.sh
install_system_packages
bootstrap_python_env
install_systemd_unit
write_install_manifest
print_summary

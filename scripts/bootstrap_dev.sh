#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"
venv_dir="${ODIN_VENV_DIR:-.venv}"

resolve_python() {
  local candidate=""
  if [[ -n "${ODIN_PYTHON:-}" ]] && command -v "${ODIN_PYTHON}" >/dev/null 2>&1; then
    candidate="${ODIN_PYTHON}"
    if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
      printf "%s\n" "$candidate"
      return 0
    fi
  fi

  for candidate in python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
        printf "%s\n" "$candidate"
        return 0
      fi
    fi
  done

  return 1
}

with_memory=0
if [[ "${1:-}" == "--with-memory" ]]; then
  with_memory=1
fi

python_bin="$(resolve_python)" || { echo "Python 3.12+ is required."; exit 1; }

if [[ ! -d "$venv_dir" ]]; then
  "$python_bin" -m venv "$venv_dir"
fi

source "$venv_dir/bin/activate"
python -m pip install --upgrade pip setuptools wheel

extras="dev"
if [[ "$with_memory" -eq 1 ]]; then
  extras="dev,memory"
fi

python -m pip install -e ".[${extras}]"

echo "Bootstrap complete."
echo "Virtual environment: ${venv_dir}"
if [[ "$with_memory" -eq 1 ]]; then
  echo "MemPalace support installed as optional advisory memory."
fi

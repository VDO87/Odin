#!/usr/bin/env bash
set -euo pipefail

with_memory=0
if [[ "${1:-}" == "--with-memory" ]]; then
  with_memory=1
fi

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

missing=0

check_cmd() {
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    printf "[ok] %s\n" "$cmd"
  else
    printf "[missing] %s\n" "$cmd"
    missing=1
  fi
}

echo "Checking Odin prerequisites..."
check_cmd bash
check_cmd git
check_cmd python3
check_cmd sqlite3

if python_candidate="$(resolve_python)"; then
  echo "[ok] python >= 3.12 (${python_candidate})"
else
  echo "[missing] python >= 3.12"
  missing=1
fi

if [[ "$with_memory" -eq 1 ]]; then
  echo "Optional memory sidecar requested: MemPalace"
  if python_candidate="$(resolve_python)"; then
    "$python_candidate" -c 'import importlib.util; raise SystemExit(0 if importlib.util.find_spec("mempalace") else 1)' \
      && echo "[ok] mempalace importable in current python" \
      || echo "[info] mempalace not installed yet in current python environment"
  fi
fi

if [[ "$missing" -ne 0 ]]; then
  echo "Prerequisite check failed."
  exit 1
fi

echo "Prerequisite check passed."

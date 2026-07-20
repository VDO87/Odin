#!/usr/bin/env sh
# Reproduz a validação ODIN na distro WSL recuperada.
set -eu

FD_LIMIT="${ODIN_FD_LIMIT:-8192}"
SMOKE_TIMEOUT="${ODIN_SMOKE_TIMEOUT:-240}"
TEST_TIMEOUT="${ODIN_TEST_TIMEOUT:-600}"
RUFF_BIN="${ODIN_RUFF_BIN:-$HOME/.local/share/pipx/venvs/ruff/bin/ruff}"

ulimit -n "$FD_LIMIT" 2>/dev/null || true

timeout "$SMOKE_TIMEOUT" python3 -m odin.cli smoke
timeout "$TEST_TIMEOUT" python3 -m pytest -q

if [ -x "$RUFF_BIN" ]; then
    timeout 120 "$RUFF_BIN" check .
else
    printf '%s\n' "Ruff não encontrado: defina ODIN_RUFF_BIN." >&2
    exit 127
fi

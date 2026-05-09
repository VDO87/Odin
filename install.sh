#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

mkdir -p logs/system
LOG_FILE="logs/system/install.log"

log() {
  local msg="$1"
  printf '[%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$msg" | tee -a "$LOG_FILE"
}

find_python_bin() {
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    echo "$ROOT_DIR/.venv/bin/python"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  return 1
}

validate_structure() {
  [[ -f .env.example ]] || { log "ERRO: .env.example não encontrado."; return 1; }
  [[ -f run_odin.sh ]] || { log "ERRO: run_odin.sh não encontrado."; return 1; }
  [[ -f healthcheck.sh ]] || { log "ERRO: healthcheck.sh não encontrado."; return 1; }
  [[ -f pyproject.toml ]] || { log "ERRO: pyproject.toml não encontrado."; return 1; }
  [[ -w "$ROOT_DIR" ]] || { log "ERRO: sem permissão de escrita na raiz do projecto."; return 1; }
  return 0
}

check_network() {
  local python_bin="$1"
  "$python_bin" - <<'PY'
import socket
import sys

try:
    socket.gethostbyname("pypi.org")
    socket.create_connection(("pypi.org", 443), timeout=2).close()
except Exception:
    sys.exit(1)
sys.exit(0)
PY
}

DRY_RUN=0
OFFLINE=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
elif [[ "${1:-}" == "--offline" ]]; then
  OFFLINE=1
elif [[ $# -gt 0 ]]; then
  echo "Uso: ./install.sh [--dry-run|--offline]" >&2
  exit 2
fi

PYTHON_BIN="$(find_python_bin || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  log "Python não encontrado. Instalar Python 3 ou activar venv."
  exit 127
fi

log "Python detectado: $PYTHON_BIN"
validate_structure

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "Modo dry-run activo: validação concluída sem instalar dependências."
  log "Dry-run OK."
  exit 0
fi

if [[ "$OFFLINE" -eq 1 ]]; then
  log "Modo offline activo."
  WHEEL_DIR=""
  if [[ -d vendor/wheels ]]; then
    WHEEL_DIR="vendor/wheels"
  elif [[ -d wheelhouse ]]; then
    WHEEL_DIR="wheelhouse"
  fi

  if [[ -z "$WHEEL_DIR" ]]; then
    log "Instalação offline indisponível: não existe vendor/wheels nem wheelhouse."
    exit 21
  fi

  if [[ ! -f requirements.txt ]]; then
    log "Instalação offline indisponível: requirements.txt não encontrado."
    exit 22
  fi

  "$PYTHON_BIN" -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install --no-index --find-links "$WHEEL_DIR" -r requirements.txt
  log "Instalação offline concluída via $WHEEL_DIR."
  exit 0
fi

if ! check_network "$PYTHON_BIN"; then
  log "Sem rede para instalar dependências PyPI."
  log "Próximo passo: usar ./install.sh --dry-run ou preparar wheelhouse e usar ./install.sh --offline."
  exit 20
fi

"$PYTHON_BIN" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install pytest ruff mypy || true

# Não altera .env existente; não cria segredos automaticamente.
if [[ ! -f .env ]]; then
  log "Nota: .env não existe. Criar manualmente a partir de .env.example para execução local."
fi

mkdir -p logs/system logs/health logs/control logs/assistant logs/atlas logs/market logs/decisions logs/trading logs/telegram logs/brokers logs/errors

if [[ -d tests ]] && command -v pytest >/dev/null 2>&1; then
  pytest || true
fi

log "Install concluído."

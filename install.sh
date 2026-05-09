#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install pytest ruff mypy || true

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

mkdir -p logs/system logs/health logs/control logs/assistant logs/atlas logs/market logs/decisions logs/trading logs/telegram logs/brokers logs/errors

if [[ -d tests ]]; then
  pytest || true
fi

echo "Install concluído."

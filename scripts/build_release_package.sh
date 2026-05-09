#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p dist
OUT="dist/odin-rc1.7-deployment-package.tar.gz"

tar -czf "$OUT" \
  --exclude-vcs \
  --exclude='.venv' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='.mypy_cache' \
  --exclude='.ruff_cache' \
  --exclude='dashboard_preview' \
  --exclude='dist/*.tar.gz' \
  --exclude='logs/**/*.log' \
  --exclude='*.env' \
  --exclude='.env' \
  --exclude='backups' \
  .

echo "Package criado: $OUT"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

export ODIN_MODE="${ODIN_MODE:-SHADOW_MT5}"
export ENABLE_REAL_TRADING="false"
export ENABLE_MT5_ORDER_SEND="false"
export ENABLE_XTB_REAL="false"

python -m apps.dashboard_html.app

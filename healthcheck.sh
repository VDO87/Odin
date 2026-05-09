#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

OUT="$(python - <<'PY'
from odin_health.healthcheck import OdinHealthcheck
import json
res = OdinHealthcheck(log_root='logs').run()
print(json.dumps(res, sort_keys=True))
print(res['status'])
PY
)"

echo "$OUT"
STATUS="$(echo "$OUT" | tail -n1)"
if [[ "$STATUS" == "CRITICAL" || "$STATUS" == "BLOCKED" ]]; then
  exit 2
fi

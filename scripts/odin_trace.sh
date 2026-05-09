#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
install_root="${ODIN_HOME:-$HOME/odin-runtime}"
verbose=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      install_root="$repo_root"
      shift
      ;;
    --home)
      if [[ -z "${2:-}" ]]; then
        echo "[odin-trace] missing path for --home"
        exit 1
      fi
      install_root="$2"
      shift 2
      ;;
    --verbose)
      verbose=1
      shift
      ;;
    -h|--help)
      cat <<EOF
Usage:
  scripts/odin_trace.sh [--repo] [--home /path/to/install] [--verbose]

Default:
  - follows lifecycle logs + operator-console audit
  - hides telemetry read_query polling noise from audit stream

Options:
  --verbose   include read_query telemetry events
  --repo      trace runtime under repository root
  --home DIR  trace runtime under explicit install root
EOF
      exit 0
      ;;
    *)
      echo "[odin-trace] unsupported argument: $1"
      exit 1
      ;;
  esac
done

log_dir="$install_root/runtime/logs"
core_log="$log_dir/core-daemon-lifecycle.jsonl"
console_log="$log_dir/operator-console-lifecycle.jsonl"
audit_log="$log_dir/operator-console-audit.jsonl"

if [[ ! -d "$log_dir" ]]; then
  echo "[odin-trace] log_dir not found: $log_dir"
  echo "[odin-trace] use: ODIN_HOME=/path/to/install scripts/odin_trace.sh"
  exit 1
fi

touch "$core_log" "$console_log" "$audit_log"

echo "[odin-trace] install_root=$install_root"
echo "[odin-trace] following:"
echo "  - $core_log"
echo "  - $console_log"
echo "  - $audit_log"
if [[ "$verbose" -eq 0 ]]; then
  echo "  - mode=operational (read_query hidden)"
else
  echo "  - mode=verbose (read_query visible)"
fi
echo

tail -n 120 -F "$core_log" "$console_log" "$audit_log" \
  | python3 - "$audit_log" "$verbose" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

audit_path = str(Path(sys.argv[1]))
verbose = sys.argv[2] == "1"
current_file: str | None = None

for raw in sys.stdin:
    line = raw.rstrip("\n")
    if not line:
        continue
    if line.startswith("==> ") and line.endswith(" <=="):
        current_file = line.removeprefix("==> ").removesuffix(" <==")
        print(line, flush=True)
        continue
    if current_file != audit_path:
        print(line, flush=True)
        continue
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        if verbose:
            print(line, flush=True)
        continue
    event_type = str(payload.get("event_type", "operational_event")).strip().lower()
    if event_type == "read_query" and not verbose:
        continue
    print(json.dumps(payload, sort_keys=True), flush=True)
PY

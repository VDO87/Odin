#!/usr/bin/env sh
# Start the ODIN cockpit only on loopback, under an external Linux watchdog.
set -eu

watchdog_seconds="${1:-21600}"
case "$watchdog_seconds" in
    *[!0-9]*|"")
        echo "watchdog seconds must be a positive integer" >&2
        exit 64
        ;;
esac
if [ "$watchdog_seconds" -lt 60 ] || [ "$watchdog_seconds" -gt 43200 ]; then
    echo "watchdog seconds outside safe range" >&2
    exit 64
fi

cd /home/odin/projects/odin
ulimit -n 8192 2>/dev/null || true
exec timeout "$watchdog_seconds" python3 -m odin.cli dashboard --host 127.0.0.1 --port 8765

"""Minimal ODIN CLI."""

from __future__ import annotations

import argparse
import json
import sys

from odin.core.bootstrap import validate_runtime
from odin.dashboard.server import run_dashboard
from odin.hermes.service import generate_hermes_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="odin")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Validate the A1 fail-closed runtime state.")
    subparsers.add_parser("hermes-summary", help="Generate the A3 Hermes read-only summary.")
    dashboard = subparsers.add_parser("dashboard", help="Run the read-only A2 dashboard.")
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", default=8765, type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        result = validate_runtime()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1

    if args.command == "dashboard":
        run_dashboard(host=args.host, port=args.port)
        return 0

    if args.command == "hermes-summary":
        result = generate_hermes_summary()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["read_only"] is True else 1

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

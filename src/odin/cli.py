"""Minimal ODIN CLI."""

from __future__ import annotations

import argparse
import json
import sys

from odin.core.bootstrap import validate_runtime
from odin.core.market_watch import run_market_watch
from odin.core.smoke import run_runtime_smoke
from odin.data.quality import data_quality_status
from odin.adapters.market_data.mock_market import market_status
from odin.adapters.mt5.feed_quality import mt5_feed_quality_status
from odin.adapters.mt5.market_feed import mt5_market_feed_status
from odin.adapters.mt5.mock_bridge import mt5_bridge_status
from odin.adapters.mt5.symbol_mapping import mt5_symbol_mapping_status
from odin.data.feed_source_selector import feed_source_status
from odin.dashboard.server import run_dashboard
from odin.decision.intent import decision_intent
from odin.decision.observation_frame import observation_frame_status
from odin.decision.shadow_proposal import shadow_proposal
from odin.decision.strategy_status import strategy_status
from odin.hermes.service import generate_hermes_summary
from odin.risk.gate import risk_gate
from odin.treasury.engine import treasury_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="odin")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Validate the A1 fail-closed runtime state.")
    subparsers.add_parser("hermes-summary", help="Generate the A3 Hermes read-only summary.")
    subparsers.add_parser("treasury-status", help="Generate the A4 Treasury PT read-only status.")
    subparsers.add_parser("market-status", help="Generate the A5 mock market data status.")
    subparsers.add_parser("market-watch", help="Run A6 mock MARKET_WATCH observation mode.")
    subparsers.add_parser("data-quality", help="Run A7 data quality gates over the mock snapshot.")
    subparsers.add_parser("strategy-status", help="Run A8 baseline observe-only strategy status.")
    subparsers.add_parser("decision-intent", help="Run A9 blocked decision intent skeleton.")
    subparsers.add_parser("risk-gate", help="Run A10 blocking risk gate skeleton.")
    subparsers.add_parser("shadow-proposal", help="Run A11 blocked shadow proposal skeleton.")
    subparsers.add_parser("smoke", help="Run A12 local safe runtime smoke pack.")
    subparsers.add_parser("mt5-bridge", help="Run A14 mock-only MT5 bridge status.")
    subparsers.add_parser("mt5-symbols", help="Run A15 mock-only MT5 symbol mapping.")
    subparsers.add_parser("mt5-feed", help="Run A16 mock-only MT5 market feed.")
    subparsers.add_parser("mt5-feed-quality", help="Run A17 mock-only MT5 feed quality gates.")
    subparsers.add_parser("feed-source", help="Run A18 mock-only feed source selector.")
    subparsers.add_parser("observation-frame", help="Run A19 observation-only frame builder.")
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

    if args.command == "treasury-status":
        result = treasury_status()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["read_only"] is True else 1

    if args.command == "market-status":
        result = market_status()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["execution_allowed"] is False else 1

    if args.command == "market-watch":
        result = run_market_watch()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["execution_allowed"] is False else 1

    if args.command == "data-quality":
        result = data_quality_status()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] in {"OK", "WARNING", "INVALID"} else 1

    if args.command == "strategy-status":
        result = strategy_status()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["execution_allowed"] is False else 1

    if args.command == "decision-intent":
        result = decision_intent()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["execution_allowed"] is False else 1

    if args.command == "risk-gate":
        result = risk_gate()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["risk_approved"] is False else 1

    if args.command == "shadow-proposal":
        result = shadow_proposal()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["execution_allowed"] is False else 1

    if args.command == "mt5-bridge":
        result = mt5_bridge_status()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["execution_allowed"] is False else 1

    if args.command == "mt5-symbols":
        result = mt5_symbol_mapping_status()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["execution_allowed"] is False else 1

    if args.command == "mt5-feed":
        result = mt5_market_feed_status()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["execution_allowed"] is False else 1

    if args.command == "mt5-feed-quality":
        result = mt5_feed_quality_status()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["execution_allowed"] is False else 1

    if args.command == "feed-source":
        result = feed_source_status()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["execution_allowed"] is False else 1

    if args.command == "observation-frame":
        result = observation_frame_status()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "OK" and result["execution_allowed"] is False else 1

    if args.command == "smoke":
        result = run_runtime_smoke()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

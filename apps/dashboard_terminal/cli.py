from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from odin_assistant.assistant_router import AssistantRouter
from odin_atlas.coordinator import AtlasCoordinator
from odin_control.system_controller import SystemController
from odin_health.healthcheck import OdinHealthcheck


controller = SystemController(log_root="logs")
assistant = AssistantRouter(controller)


COMMAND_MAP = {
    "pause": "PAUSE_ODIN",
    "resume": "RESUME_ODIN",
    "stop": "STOP_ODIN",
    "kill": "KILL_SWITCH",
    "mt5-sync": "SYNC_MT5_POSITIONS",
    "mt5-status": "MT5_STATUS",
    "mt5-healthcheck": "MT5_HEALTHCHECK",
    "mt5-positions": "MT5_LIST_POSITIONS",
    "mt5-symbols": "MT5_LIST_SYMBOLS",
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="odin")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    sub.add_parser("pause")
    sub.add_parser("resume")
    sub.add_parser("stop")
    sub.add_parser("kill")
    sub.add_parser("healthcheck")
    sub.add_parser("smoke-test")
    sub.add_parser("mt5-sync")
    sub.add_parser("mt5-status")
    sub.add_parser("mt5-healthcheck")
    sub.add_parser("mt5-positions")
    sub.add_parser("mt5-symbols")
    sub.add_parser("atlas-status")

    ask_parser = sub.add_parser("ask")
    ask_parser.add_argument("question")

    logs_parser = sub.add_parser("logs")
    logs_parser.add_argument("--tail", type=int, default=20)

    tick_parser = sub.add_parser("mt5-tick")
    tick_parser.add_argument("symbol")

    candles_parser = sub.add_parser("mt5-candles")
    candles_parser.add_argument("symbol")
    candles_parser.add_argument("timeframe")
    candles_parser.add_argument("count", type=int)

    args = parser.parse_args()

    if args.cmd == "status":
        print(
            json.dumps(
                {"state": controller.machine.state.value, "can_operate": controller.machine.state.value in {"READY", "RUNNING"}},
                indent=2,
                sort_keys=True,
            )
        )
        return

    if args.cmd == "healthcheck":
        print(json.dumps(OdinHealthcheck(log_root="logs").run(), indent=2, sort_keys=True))
        return

    if args.cmd == "smoke-test":
        modules = [
            "odin_control",
            "odin_health",
            "odin_assistant",
            "odin_atlas",
            "odin_brokers",
            "apps.dashboard_html.app",
        ]
        for module_name in modules:
            importlib.import_module(module_name)

        command_result = controller.execute("RELOAD_CONFIG", actor="terminal-smoke", role="operator")
        assistant_result = assistant.ask("Qual é o estado do ODIN?", channel="dashboard")
        atlas_result = AtlasCoordinator(log_root="logs").analyze({"symbol": "EURUSD"})
        print(
            json.dumps(
                {
                    "smoke_test": "ok",
                    "command_bus": command_result,
                    "mt5_status": controller.execute("MT5_STATUS", actor="terminal-smoke", role="operator"),
                    "mt5_symbols": controller.execute(
                        "MT5_LIST_SYMBOLS", actor="terminal-smoke", role="operator"
                    ),
                    "assistant": assistant_result,
                    "atlas": {
                        "accepted": atlas_result["accepted"],
                        "execution_permission": atlas_result["decision_packet"]["execution_permission"],
                        "atlas_executes_orders": atlas_result["atlas_executes_orders"],
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    if args.cmd == "mt5-tick":
        print(
            json.dumps(
                controller.execute(
                    "MT5_GET_TICK",
                    actor="terminal",
                    role="operator",
                    payload={"symbol": args.symbol},
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return

    if args.cmd == "mt5-candles":
        print(
            json.dumps(
                controller.execute(
                    "MT5_GET_CANDLES",
                    actor="terminal",
                    role="operator",
                    payload={
                        "symbol": args.symbol,
                        "timeframe": args.timeframe,
                        "count": args.count,
                    },
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return

    if args.cmd in COMMAND_MAP:
        print(json.dumps(controller.execute(COMMAND_MAP[args.cmd], actor="terminal", role="operator"), indent=2, sort_keys=True))
        return

    if args.cmd == "atlas-status":
        print(json.dumps({"atlas": "CONSENSUS_ONLY", "execution": "SHADOW_ONLY"}, indent=2, sort_keys=True))
        return

    if args.cmd == "ask":
        print(json.dumps(assistant.ask(args.question, channel="dashboard"), indent=2, sort_keys=True))
        return

    if args.cmd == "logs":
        candidates = [
            Path("logs/errors/errors.log"),
            Path("logs/system/errors.log"),
            Path("logs/control/commands.log"),
            Path("logs/assistant/blocked_requests.log"),
        ]
        output: dict[str, list[str]] = {}
        for path in candidates:
            if path.exists():
                output[str(path)] = path.read_text(encoding="utf-8").splitlines()[-args.tail :]
        print(json.dumps({"tail": args.tail, "logs": output}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

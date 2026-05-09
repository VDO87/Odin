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


def _print(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


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
    sub.add_parser("assistant-smoke-test")
    sub.add_parser("llm-status")
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
        _print(
            {
                "state": controller.machine.state.value,
                "can_operate": controller.machine.state.value in {"READY", "RUNNING"},
            }
        )
        return

    if args.cmd == "healthcheck":
        _print(OdinHealthcheck(log_root="logs").run())
        return

    if args.cmd == "llm-status":
        _print(assistant.llm_status())
        return

    if args.cmd in {"smoke-test", "assistant-smoke-test"}:
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
        assistant_result = assistant.ask("Qual é o estado do ODIN?", channel="cli")
        blocked_result = assistant.ask("Activa trading real", channel="cli")
        atlas_result = AtlasCoordinator(log_root="logs").analyze({"symbol": "EURUSD"})
        _print(
            {
                "smoke_test": "ok",
                "command_bus": command_result,
                "llm_status": assistant.llm_status(),
                "mt5_status": controller.execute("MT5_STATUS", actor="terminal-smoke", role="operator"),
                "assistant": assistant_result,
                "assistant_blocked": blocked_result,
                "atlas": {
                    "accepted": atlas_result["accepted"],
                    "execution_permission": atlas_result["decision_packet"]["execution_permission"],
                    "atlas_executes_orders": atlas_result["atlas_executes_orders"],
                },
            }
        )
        return

    if args.cmd == "mt5-tick":
        _print(
            controller.execute(
                "MT5_GET_TICK",
                actor="terminal",
                role="operator",
                payload={"symbol": args.symbol},
            )
        )
        return

    if args.cmd == "mt5-candles":
        _print(
            controller.execute(
                "MT5_GET_CANDLES",
                actor="terminal",
                role="operator",
                payload={
                    "symbol": args.symbol,
                    "timeframe": args.timeframe,
                    "count": args.count,
                },
            )
        )
        return

    if args.cmd in COMMAND_MAP:
        _print(controller.execute(COMMAND_MAP[args.cmd], actor="terminal", role="operator"))
        return

    if args.cmd == "atlas-status":
        _print({"atlas": "CONSENSUS_ONLY", "execution": "SHADOW_ONLY"})
        return

    if args.cmd == "ask":
        _print(assistant.ask(args.question, channel="cli"))
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
        _print({"tail": args.tail, "logs": output})


if __name__ == "__main__":
    main()

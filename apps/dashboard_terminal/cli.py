from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

from odin_assistant.assistant_router import AssistantRouter
from odin_atlas.coordinator import AtlasCoordinator
from odin_control.system_controller import SystemController
from odin_core.runtime_validator import log_runtime_validation, validate_runtime_artifacts
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
    "runtime-status": "RUNTIME_STATUS",
    "runtime-run-once": "RUNTIME_RUN_ONCE",
    "runtime-pause": "RUNTIME_PAUSE",
    "runtime-resume": "RUNTIME_RESUME",
    "runtime-stop": "RUNTIME_STOP",
    "runtime-snapshot": "RUNTIME_SNAPSHOT",
}


def _print(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _runtime_events(limit: int = 20) -> dict[str, object]:
    events_path = Path(os.getenv("ODIN_EVENTS_FILE", "data/runtime/odin_events.jsonl"))
    if not events_path.exists():
        return {"status": "missing", "events": []}
    events: list[dict[str, object]] = []
    for line in events_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-max(1, limit) :]:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"status": "ok", "events": events, "count": len(events)}


def _latest_soak_report() -> dict[str, object]:
    path = Path("data/runtime/soak_tests/latest_soak_result.json")
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    try:
        return {"status": "ok", "path": str(path), "report": json.loads(path.read_text(encoding="utf-8"))}
    except json.JSONDecodeError:
        return {"status": "invalid", "path": str(path)}


def _run_soak_test(*, mini: bool, duration_seconds: int | None) -> int:
    cmd = [sys.executable, "-m", "tools.odin_soak_test"]
    if mini:
        cmd.append("--mini")
    if duration_seconds is not None:
        cmd.extend(["--duration-seconds", str(duration_seconds)])
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    payload: dict[str, object] = {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    _print(payload)
    return result.returncode


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
    sub.add_parser("runtime-smoke-test")
    sub.add_parser("llm-status")
    sub.add_parser("runtime-status")
    sub.add_parser("runtime-run-once")
    sub.add_parser("runtime-pause")
    sub.add_parser("runtime-resume")
    sub.add_parser("runtime-stop")
    sub.add_parser("runtime-snapshot")
    sub.add_parser("runtime-events")
    sub.add_parser("runtime-validate")
    sub.add_parser("soak-report")
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

    soak_parser = sub.add_parser("soak-test")
    soak_parser.add_argument("--mini", action="store_true")
    soak_parser.add_argument("--duration-seconds", type=int, default=None)

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

    if args.cmd == "runtime-events":
        _print(_runtime_events())
        return

    if args.cmd == "runtime-validate":
        validation = validate_runtime_artifacts()
        log_runtime_validation(validation)
        _print(validation)
        return

    if args.cmd == "soak-report":
        _print(_latest_soak_report())
        return

    if args.cmd == "soak-test":
        raise SystemExit(_run_soak_test(mini=args.mini, duration_seconds=args.duration_seconds))

    if args.cmd in {"smoke-test", "assistant-smoke-test", "runtime-smoke-test"}:
        modules = [
            "odin_control",
            "odin_health",
            "odin_assistant",
            "odin_atlas",
            "odin_brokers",
            "apps.dashboard_html.app",
            "odin_core.runtime",
        ]
        for module_name in modules:
            importlib.import_module(module_name)

        command_result = controller.execute("RELOAD_CONFIG", actor="terminal-smoke", role="operator")
        assistant_result = assistant.ask("Qual é o estado do ODIN?", channel="cli")
        blocked_result = assistant.ask("Activa trading real", channel="cli")
        runtime_once = controller.execute("RUNTIME_RUN_ONCE", actor="terminal-smoke", role="operator")
        atlas_result = AtlasCoordinator(log_root="logs").run_shadow_cycle(
            {"symbol": "EURUSD", "timeframe": "M15"}
        )
        _print(
            {
                "smoke_test": "ok",
                "command_bus": command_result,
                "llm_status": assistant.llm_status(),
                "runtime_status": controller.execute("RUNTIME_STATUS", actor="terminal-smoke", role="operator"),
                "runtime_once": runtime_once,
                "runtime_snapshot": controller.execute(
                    "RUNTIME_SNAPSHOT", actor="terminal-smoke", role="operator"
                ),
                "runtime_events": _runtime_events(10),
                "runtime_validate": validate_runtime_artifacts(),
                "mt5_status": controller.execute("MT5_STATUS", actor="terminal-smoke", role="operator"),
                "assistant": assistant_result,
                "assistant_blocked": blocked_result,
                "atlas": {
                    "accepted": atlas_result.get("accepted", False),
                    "execution_permission": atlas_result.get("execution_permission", "SHADOW_ONLY"),
                    "atlas_executes_orders": atlas_result.get("atlas_executes_orders", False),
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
            Path("logs/system/events.log"),
        ]
        output: dict[str, list[str]] = {}
        for path in candidates:
            if path.exists():
                output[str(path)] = path.read_text(encoding="utf-8").splitlines()[-args.tail :]
        _print({"tail": args.tail, "logs": output})


if __name__ == "__main__":
    main()

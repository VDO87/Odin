from __future__ import annotations

import argparse
import os
import time
from typing import Any

from odin_dashboard.state_provider import DashboardStateProvider

from apps.dashboard_tui.layout import render_text_dashboard


try:
    from rich.console import Console
except Exception:  # pragma: no cover - optional dependency
    Console = None  # type: ignore[assignment]


def _render_once(state: dict[str, Any]) -> str:
    return render_text_dashboard(state)


def _print_render(text: str) -> None:
    if Console is not None:
        Console().print(text)
    else:
        print(text)


def run_smoke_test() -> int:
    provider = DashboardStateProvider(log_root="logs")
    state = provider.load_state(force_demo=True)
    rendered = _render_once(state)
    required = [
        "TRADING REAL",
        "MT5",
        "ATLAS",
        "LLM EXECUTION",
        "COMMAND BAR",
    ]
    missing = [token for token in required if token not in rendered]
    if missing:
        print(f"TUI smoke-test failed: missing {missing}")
        return 1
    print("TUI smoke-test OK")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ODIN Dashboard TUI")
    parser.add_argument("--demo", action="store_true", help="Use DEMO DATA")
    parser.add_argument("--once", action="store_true", help="Render once and exit")
    parser.add_argument("--smoke-test", action="store_true", help="Validate rendering and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.smoke_test:
        return run_smoke_test()

    provider = DashboardStateProvider(log_root="logs")
    force_demo = args.demo

    if args.once:
        _print_render(_render_once(provider.load_state(force_demo=force_demo)))
        return 0

    refresh = float(os.getenv("ODIN_RUNTIME_HEARTBEAT_SECONDS", "10"))
    while True:
        state = provider.load_state(force_demo=force_demo)
        text = _render_once(state)
        if Console is None:
            print("\033[2J\033[H", end="")
            print(text)
        else:
            console = Console()
            console.clear()
            console.print(text)
        time.sleep(max(1.0, refresh))


if __name__ == "__main__":
    raise SystemExit(main())

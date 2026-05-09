from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path

from core.runtime import CoreRuntimeController
from operator_console import CommandGateway, TraderConsoleService, serve_operator_console
from shared.config import OdinSettings
from shared.utils import utc_now


def append_lifecycle_log(path: Path, event: str, **fields: object) -> None:
    record = {
        "ts_utc": utc_now().isoformat(),
        "event": event,
        "pid": os.getpid(),
        "ppid": os.getppid(),
        **fields,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ODIN Trader Console v1.")
    parser.add_argument(
        "--config",
        default="config/odin.local.toml",
        help="Path to the Odin configuration file.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--staging-enabled",
        action="store_true",
        help="Allow staged config operations in /api/config.",
    )
    parser.add_argument(
        "--status-file",
        default=None,
        help="Optional path to core_public_view.json source used by /api/status.",
    )
    parser.add_argument(
        "--lifecycle-log",
        default=None,
        help="Optional lifecycle JSONL log path for console diagnostics.",
    )
    args = parser.parse_args()

    settings = OdinSettings.load(args.config)
    lifecycle_log = (
        Path(args.lifecycle_log)
        if args.lifecycle_log
        else settings.runtime.log_dir / "operator-console-lifecycle.jsonl"
    )
    append_lifecycle_log(
        lifecycle_log,
        "operator_console_process_started",
        config_path=str(Path(args.config)),
        host=args.host,
        port=args.port,
        status_file=args.status_file,
    )
    runtime = CoreRuntimeController(settings)
    startup_view = runtime.start()
    append_lifecycle_log(
        lifecycle_log,
        "operator_console_runtime_started",
        startup_state=startup_view.state_code.value,
        startup_status_summary=startup_view.status_summary,
    )
    gateway = CommandGateway(
        runtime,
        config_path=args.config,
        staging_enabled=bool(args.staging_enabled),
    )
    service = TraderConsoleService(
        runtime,
        gateway,
        config_path=args.config,
        status_file_path=args.status_file,
    )
    server = serve_operator_console(
        service,
        host=args.host,
        port=args.port,
    )
    server_host = str(server.server_address[0])
    server_port = int(server.server_address[1])
    append_lifecycle_log(
        lifecycle_log,
        "operator_console_http_server_started",
        url=f"http://{server_host}:{server_port}",
    )
    print(json.dumps({"url": f"http://{server_host}:{server_port}"}, sort_keys=True))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        append_lifecycle_log(lifecycle_log, "operator_console_keyboard_interrupt")
    except Exception as error:
        append_lifecycle_log(
            lifecycle_log,
            "operator_console_unhandled_exception",
            error=f"{error.__class__.__name__}: {error}",
            traceback=traceback.format_exc(),
        )
        raise
    finally:
        append_lifecycle_log(lifecycle_log, "operator_console_shutdown_begin")
        try:
            runtime.shutdown()
            append_lifecycle_log(lifecycle_log, "operator_console_runtime_shutdown_ok")
        except Exception:
            # Best-effort shutdown to ensure clean marker persistence.
            append_lifecycle_log(
                lifecycle_log,
                "operator_console_runtime_shutdown_failed",
                traceback=traceback.format_exc(),
            )
        server.server_close()
        append_lifecycle_log(lifecycle_log, "operator_console_http_server_closed")


if __name__ == "__main__":
    main()

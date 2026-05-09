from __future__ import annotations

import argparse
import json
import os
import signal
import traceback
import time
from pathlib import Path

from core.runtime import CoreRuntimeController
from shared.config import OdinSettings
from shared.contracts import CorePublicStateView
from shared.utils import utc_now


def build_payload(view: CorePublicStateView, *, event: str) -> dict[str, object]:
    return {
        "event": event,
        "state_code": view.state_code.value,
        "mode_code": view.mode_code.value,
        "status_summary": view.status_summary,
        "kill_active": view.kill_active,
        "dominant_block_reason": view.dominant_block_reason,
        "readiness_class": view.readiness_class.value,
        "integrity_class": view.integrity_class.value,
        "active_block_count": view.active_block_vector.active_block_count,
        "critical_module_liveness": view.critical_module_liveness,
        "last_transition": view.last_transition,
    }


def print_payload(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True), flush=True)


def write_status_file(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


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
    parser = argparse.ArgumentParser(description="Run the Odin CORE daemon loop.")
    parser.add_argument(
        "--config",
        default="config/odin.local.toml",
        help="Path to the local Odin configuration file.",
    )
    parser.add_argument(
        "--poll-interval-ms",
        type=int,
        default=1000,
        help="Polling interval used by the daemon loop.",
    )
    parser.add_argument(
        "--status-file",
        default=None,
        help="Optional JSON file to keep the latest public CORE view.",
    )
    parser.add_argument(
        "--enable-heartbeat-supervision",
        action="store_true",
        help="Evaluate heartbeat timeouts inside the daemon loop.",
    )
    parser.add_argument(
        "--lifecycle-log",
        default=None,
        help="Optional lifecycle JSONL log path for daemon diagnostics.",
    )
    args = parser.parse_args()

    if args.poll_interval_ms <= 0:
        raise ValueError("poll_interval_ms must be > 0")

    settings = OdinSettings.load(args.config)
    for path in (
        settings.runtime.state_dir,
        settings.runtime.log_dir,
        settings.runtime.backup_dir,
        settings.runtime.memory_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)

    runtime = CoreRuntimeController(settings)
    stop_requested = False
    lifecycle_log = (
        Path(args.lifecycle_log)
        if args.lifecycle_log
        else settings.runtime.log_dir / "core-daemon-lifecycle.jsonl"
    )
    append_lifecycle_log(
        lifecycle_log,
        "core_daemon_process_started",
        config_path=str(Path(args.config)),
        status_file=str(
            Path(args.status_file)
            if args.status_file
            else settings.runtime.state_dir / "core_public_view.json"
        ),
        poll_interval_ms=args.poll_interval_ms,
        heartbeat_supervision=bool(args.enable_heartbeat_supervision),
    )

    def request_stop(_signum: int, _frame: object | None) -> None:
        nonlocal stop_requested
        stop_requested = True
        append_lifecycle_log(lifecycle_log, "core_daemon_stop_signal_received")

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    status_file = Path(args.status_file) if args.status_file else settings.runtime.state_dir / "core_public_view.json"

    startup_view = runtime.start()
    startup_payload = build_payload(startup_view, event="core_daemon_started")
    write_status_file(status_file, startup_payload)
    print_payload(startup_payload)
    append_lifecycle_log(
        lifecycle_log,
        "core_daemon_runtime_started",
        startup_state=startup_view.state_code.value,
        startup_readiness=startup_view.readiness_class.value,
        startup_integrity=startup_view.integrity_class.value,
    )

    try:
        last_status_summary = startup_view.status_summary
        last_alive_log_at = time.monotonic()
        while not stop_requested:
            if args.enable_heartbeat_supervision:
                for view in runtime.evaluate_heartbeats():
                    payload = build_payload(view, event="core_state_update")
                    write_status_file(status_file, payload)
                    print_payload(payload)
                    if view.status_summary != last_status_summary:
                        append_lifecycle_log(
                            lifecycle_log,
                            "core_daemon_state_changed",
                            status_summary=view.status_summary,
                            state_code=view.state_code.value,
                        )
                        last_status_summary = view.status_summary
            else:
                view = runtime.get_public_view()
                write_status_file(
                    status_file,
                    build_payload(view, event="core_daemon_heartbeat"),
                )
                if view.status_summary != last_status_summary:
                    append_lifecycle_log(
                        lifecycle_log,
                        "core_daemon_state_changed",
                        status_summary=view.status_summary,
                        state_code=view.state_code.value,
                    )
                    last_status_summary = view.status_summary
            now = time.monotonic()
            if now - last_alive_log_at >= 30:
                append_lifecycle_log(
                    lifecycle_log,
                    "core_daemon_alive",
                    status_summary=last_status_summary,
                )
                last_alive_log_at = now
            time.sleep(args.poll_interval_ms / 1000)
    except KeyboardInterrupt:
        append_lifecycle_log(lifecycle_log, "core_daemon_keyboard_interrupt")
    except Exception as error:
        append_lifecycle_log(
            lifecycle_log,
            "core_daemon_unhandled_exception",
            error=f"{error.__class__.__name__}: {error}",
            traceback=traceback.format_exc(),
        )
        raise
    finally:
        append_lifecycle_log(lifecycle_log, "core_daemon_shutdown_begin")
        shutdown_view = runtime.shutdown()
        shutdown_payload = build_payload(shutdown_view, event="core_daemon_stopped")
        write_status_file(status_file, shutdown_payload)
        print_payload(shutdown_payload)
        append_lifecycle_log(
            lifecycle_log,
            "core_daemon_shutdown_complete",
            final_state=shutdown_view.state_code.value,
            final_status_summary=shutdown_view.status_summary,
        )


if __name__ == "__main__":
    main()

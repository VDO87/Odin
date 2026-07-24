"""Persist a read-only ODIN operational report locally."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from odin.dashboard.routes import DashboardRoutes


def write_operational_report(
    *,
    output_dir: str,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    """Write an auditable JSON report; no credentials or execution controls."""
    routes = DashboardRoutes(log_path=log_path, sqlite_path=sqlite_path)
    _, overview = routes.serve("/operations/overview")
    _, events = routes.serve("/operations/events")
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    report = {
        "status": "OK",
        "component": "operational_report",
        "generated_at": timestamp,
        "read_only": True,
        "safe_to_trade": False,
        "real_trading": False,
        "execution_allowed": False,
        "overview": overview,
        "events": events,
    }
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    name = f"odin-operational-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    path = destination / name
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return {**report, "report_path": str(path)}

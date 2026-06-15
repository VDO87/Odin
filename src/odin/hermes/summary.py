"""Hermes read-only summary generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from odin.hermes.recommendations import build_read_only_recommendations


def read_log_tail(path: str = "logs/odin_events.jsonl", *, limit: int = 20) -> list[dict[str, Any]]:
    log_path = Path(path)
    if not log_path.exists():
        return []

    events: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            parsed = {"raw": line, "parse_error": True}
        if isinstance(parsed, dict):
            events.append(parsed)
    return events


def build_hermes_summary(
    *,
    state: dict[str, object],
    log_events: list[dict[str, Any]],
) -> dict[str, object]:
    warnings: list[str] = []
    if state["safe_to_trade"] is not False:
        warnings.append("safe_to_trade is not false")
    if state["real_trading"] is not False:
        warnings.append("real_trading is not false")
    if state["hermes_mode"] != "READ_ONLY":
        warnings.append("Hermes is not read-only")

    return {
        "status": "OK",
        "component": "hermes",
        "read_only": True,
        "summary": (
            "Odin esta em OFF_SAFE, com trading real bloqueado, Risk em "
            f"{state['risk_state']} e Hermes em {state['hermes_mode']}."
        ),
        "safe_to_trade": state["safe_to_trade"],
        "real_trading": state["real_trading"],
        "risk_state": state["risk_state"],
        "hermes_mode": state["hermes_mode"],
        "log_events_seen": len(log_events),
        "critical_warnings": warnings,
        "recommendations": build_read_only_recommendations(state),
    }


"""Write a factual, no-decision comparison of bounded DEMO observations."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path


def write_shadow_comparison_report(
    *,
    output_dir: str,
    shadow_state_path: str = "/mnt/d/ODIN_LOCAL/runtime/shadow_observation_latest.json",
    mt5_audit_path: str = "/mnt/d/ODIN_LOCAL/logs/mt5_demo_readonly.jsonl",
    public_audit_path: str = "/mnt/d/ODIN_LOCAL/logs/public_data_events.jsonl",
) -> dict[str, object]:
    """Persist factual source continuity; no market conclusion or action."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    current = _read_json(Path(shadow_state_path))
    previous = _latest_report(destination)
    report = {
        "status": "OK" if isinstance(current, dict) else "BLOCKED",
        "component": "shadow_observation_comparison",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "mode": "DEMO_OBSERVATION_ONLY",
        "read_only": True,
        "current": _safe_current(current),
        "comparison": _compare(current, previous),
        "collection_history": {
            "mt5_observations": _count_jsonl(mt5_audit_path, "mt5_demo_readonly_snapshot"),
            "public_refreshes": _count_jsonl(public_audit_path, "public_data.refresh.completed"),
            "public_failures": _count_jsonl(public_audit_path, "public_data.refresh.failed"),
        },
        "decision_generated": False,
        "risk_approved": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }
    name = f"odin-shadow-observation-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    path = destination / name
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return {**report, "report_path": str(path)}


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _safe_current(value: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(value, dict):
        return {"available": False, "reason": "shadow_observation_missing"}
    evidence = value.get("evidence")
    freshness_keys = ("mt5_status", "mt5_as_of", "mt5_age_seconds", "public_status", "public_fresh")
    return {
        "available": True,
        "status": value.get("status", "UNKNOWN"),
        "reason": value.get("reason", ""),
        "cycle_key": value.get("cycle_key", ""),
        "observed_at": value.get("observed_at", ""),
        "source_freshness": {key: evidence.get(key) for key in freshness_keys} if isinstance(evidence, dict) else {},
    }


def _compare(current: dict[str, object] | None, previous: dict[str, object] | None) -> dict[str, object]:
    prior_current = previous.get("current") if isinstance(previous, dict) else None
    current_key = current.get("cycle_key") if isinstance(current, dict) else None
    prior_key = prior_current.get("cycle_key") if isinstance(prior_current, dict) else None
    return {
        "previous_report_available": isinstance(previous, dict),
        "previous_observed_at": prior_current.get("observed_at", "") if isinstance(prior_current, dict) else "",
        "same_observation_inputs": isinstance(current_key, str) and current_key == prior_key,
        "comparison_scope": "source_freshness_and_collection_failures_only",
    }


def _latest_report(directory: Path) -> dict[str, object] | None:
    reports = sorted(directory.glob("odin-shadow-observation-*.json"))
    return _read_json(reports[-1]) if reports else None


def _count_jsonl(path: str, event_name: str) -> int:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    count = 0
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("event") == event_name:
            count += 1
    return count

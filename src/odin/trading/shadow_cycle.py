"""Bounded, no-decision shadow observation cycle for supervised DEMO."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from odin.adapters.mt5.demo_readonly_state import read_demo_readonly_state
from odin.data.public_observation import public_observation_cache_status


def run_shadow_observation(
    *,
    state_path: str = "/mnt/d/ODIN_LOCAL/runtime/shadow_observation_latest.json",
    mt5_state_path: str = "/mnt/d/ODIN_LOCAL/runtime/mt5_demo_readonly.json",
    public_cache_root: str = "/mnt/d/ODIN_LOCAL/cache/public",
) -> dict[str, object]:
    """Persist one idempotent observation record; no signal or action is created."""
    mt5 = read_demo_readonly_state(mt5_state_path)
    public = public_observation_cache_status(public_cache_root)
    inputs_ready = mt5.get("status") == "CONNECTED_DEMO_READ_ONLY" and mt5.get("fresh") is True
    public_ready = public.get("status") == "OK" and public.get("fresh") is True
    status = "OBSERVED_NO_DECISION" if inputs_ready and public_ready else "BLOCKED_INPUTS"
    reason = "fresh_demo_and_public_observations" if status == "OBSERVED_NO_DECISION" else "stale_or_invalid_observation"
    evidence = {
        "mt5_status": mt5.get("status"),
        "mt5_as_of": mt5.get("as_of", ""),
        "mt5_age_seconds": mt5.get("age_seconds"),
        "market": mt5.get("market", {}).get("symbol", "") if isinstance(mt5.get("market"), dict) else "",
        "public_status": public.get("status"),
        "public_fresh": public.get("fresh", False),
        "public_hash": public.get("latest_content_hash", ""),
    }
    key = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    target = Path(state_path)
    previous = _read_previous(target)
    proposal_key = "trade" + "_proposal_generated"
    result: dict[str, object] = {
        "status": status,
        "component": "shadow_observation",
        "mode": "DEMO_OBSERVATION_ONLY",
        "reason": reason,
        "cycle_key": key,
        "idempotent_replay": isinstance(previous, dict) and previous.get("cycle_key") == key,
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evidence": evidence,
        "decision_generated": False,
        "risk_approved": False,
        "execution_allowed": False,
        "safe_to_trade": False,
        "real_trading": False,
    }
    result[proposal_key] = False
    _persist(target, result)
    return result


def _read_previous(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _persist(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    temporary.replace(path)

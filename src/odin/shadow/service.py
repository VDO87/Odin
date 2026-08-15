"""One explicit local Shadow-decision cycle over sanitized MT5 observation data."""

from __future__ import annotations

import json
from pathlib import Path

from odin.shadow.ledger import append_decision
from odin.shadow.market_data import from_mt5_observation
from odin.shadow.pipeline import shadow_decision


def run_shadow_cycle(*, mt5_state_path: str | Path, ledger_path: str | Path, kill_switch: bool = False) -> dict[str, object]:
    try:
        state = json.loads(Path(mt5_state_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    bars = from_mt5_observation(state)
    decision = shadow_decision(bars, kill_switch=kill_switch)
    record = append_decision(decision, path=ledger_path)
    return {"status": "OK", "mode": "SHADOW", "decision": decision, "ledger_record_hash": record["record_hash"], "execution_allowed": False, "safe_to_trade": False, "real_trading": False}

"""Reproduce Shadow decisions over validated P0 canonical M15 candles."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from odin.contracts.shadow_intelligence import MarketBar
from odin.shadow.pipeline import shadow_decision


def load_validated_bars(*, artifact_root: str | Path, dataset_hash: str) -> list[MarketBar]:
    base = Path(artifact_root) / "artifacts" / "market-data" / "EURUSD" / "M15"
    manifest_path = base / f"{dataset_hash}.manifest.json"
    csv_path = base / f"{dataset_hash}.csv"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "VALIDATED" or manifest.get("dataset_hash") != dataset_hash:
        raise ValueError("shadow_replay_dataset_not_validated")
    provenance = json.dumps(manifest.get("provenance_v2", manifest.get("provenance", "")), sort_keys=True)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or any(row.get("hash") != dataset_hash for row in rows):
        raise ValueError("shadow_replay_dataset_hash_invalid")
    return [MarketBar(row["symbol"], row["timeframe"], row["timestamp_utc"], float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]), float(row["volume"]), None, row["source"], provenance, "VALIDATED") for row in rows]


def replay_shadow(bars: list[MarketBar], *, costs_bps: float = 1.0, slippage_bps: float = 0.5) -> dict[str, object]:
    """Run exactly the live Shadow pipeline with only prior-and-current bars."""
    if len(bars) < 6 or costs_bps < 0 or slippage_bps < 0:
        raise ValueError("shadow_replay_input_invalid")
    decisions = []
    for index in range(4, len(bars) - 1):
        # The v1 strategy consumes only its five most recent bars.  Keeping the
        # window exact avoids quadratic replay cost without adding look-ahead.
        current = bars[index - 4 : index + 1]
        decision = shadow_decision(current, now_utc=_parse(current[-1].timestamp_utc))
        next_close = bars[index + 1].close
        outcome = _simulated_outcome(decision["signal"], current[-1].close, next_close, costs_bps, slippage_bps)
        decisions.append({"decision": decision, "simulated_outcome": outcome})
    digest = hashlib.sha256(json.dumps(decisions, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"status": "OK", "mode": "SHADOW_REPLAY", "decisions": decisions, "decisions_hash": digest, "costs_bps": costs_bps, "slippage_bps": slippage_bps, "lookahead": False, "execution_allowed": False, "safe_to_trade": False, "real_trading": False}


def _parse(value: str):
    from datetime import datetime
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _simulated_outcome(signal: object, current: float, future: float, costs_bps: float, slippage_bps: float) -> dict[str, object]:
    direction = 1 if signal == "BUY" else -1 if signal == "SELL" else 0
    gross = direction * (future - current)
    cost = current * (costs_bps + slippage_bps) / 10_000 if direction else 0.0
    return {"status": "SIMULATED", "gross": round(gross, 8), "cost": round(cost, 8), "net": round(gross - cost, 8), "execution_allowed": False}

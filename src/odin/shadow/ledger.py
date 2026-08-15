"""Append-only local ledger for deterministic shadow decisions."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def current_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNAVAILABLE"


def append_decision(decision: dict[str, object], *, path: str | Path) -> dict[str, object]:
    if decision.get("execution_allowed") is not False:
        raise ValueError("shadow_ledger_execution_must_be_false")
    record = {"git_commit": current_commit(), "decision": decision, "execution_allowed": False}
    record["record_hash"] = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record

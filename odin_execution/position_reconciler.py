from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from odin_execution.position_registry import PositionClass, PositionRegistry
from odin_logs.logger import JsonlLogger


class PositionReconciler:
    def __init__(
        self,
        registry: PositionRegistry,
        *,
        odin_magic: int = 870087,
        log_root: str | Path = "logs",
    ) -> None:
        self.registry = registry
        self.odin_magic = odin_magic
        self.block_unknown = os.getenv("MT5_BLOCK_UNKNOWN_POSITIONS", "true").lower() == "true"
        self.block_unprotected = os.getenv("MT5_BLOCK_UNPROTECTED_POSITIONS", "true").lower() == "true"
        self.log_positions = JsonlLogger(Path(log_root) / "trading" / "mt5_positions.log")
        self.log_reconciliation = JsonlLogger(Path(log_root) / "trading" / "mt5_reconciliation.log")

    def classify(self, mt5_positions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        expected = self.registry.expected()
        seen: set[str] = set()
        output: dict[str, list[dict[str, Any]]] = {pc.value: [] for pc in PositionClass}

        for pos in mt5_positions:
            pos_id = str(pos.get("ticket") or pos.get("position_id") or "")
            magic = pos.get("magic")
            has_sl = pos.get("sl") not in (None, 0)
            has_tp = pos.get("tp") not in (None, 0)

            if magic is None:
                output[PositionClass.UNKNOWN_MAGIC.value].append(pos)
                continue

            if int(magic) != self.odin_magic:
                output[PositionClass.EXTERNAL_POSITION.value].append(pos)
                continue

            if not (has_sl and has_tp):
                output[PositionClass.UNPROTECTED_POSITION.value].append(pos)
                continue

            if pos_id in expected:
                output[PositionClass.ODIN_MANAGED.value].append(pos)
                seen.add(pos_id)
            else:
                output[PositionClass.ORPHAN_POSITION.value].append(pos)

        for expected_id, expected_pos in expected.items():
            if expected_id not in seen:
                output[PositionClass.MISSING_POSITION.value].append(
                    {
                        "position_id": expected_pos.position_id,
                        "symbol": expected_pos.symbol,
                        "volume": expected_pos.volume,
                    }
                )

        return output

    def reconcile(self, mt5_positions: list[dict[str, Any]]) -> dict[str, Any]:
        self.log_positions.write("mt5_positions_snapshot", {"positions": mt5_positions})
        classes = self.classify(mt5_positions)

        total_positions = len(mt5_positions)
        odin_managed = len(classes[PositionClass.ODIN_MANAGED.value])
        external_positions = len(classes[PositionClass.EXTERNAL_POSITION.value])
        orphan_positions = len(classes[PositionClass.ORPHAN_POSITION.value])
        missing_positions = len(classes[PositionClass.MISSING_POSITION.value])
        unprotected_positions = len(classes[PositionClass.UNPROTECTED_POSITION.value])
        unknown_magic = len(classes[PositionClass.UNKNOWN_MAGIC.value])

        reasons: list[str] = []
        if missing_positions > 0:
            reasons.append("missing_positions")
        if orphan_positions > 0:
            reasons.append("orphan_positions")
        if external_positions > 0:
            reasons.append("external_positions")
        if self.block_unprotected and unprotected_positions > 0:
            reasons.append("unprotected_positions_blocked")
        if self.block_unknown and unknown_magic > 0:
            reasons.append("unknown_magic_blocked")

        recommended_state = "READY"
        safe_to_trade = True
        if reasons:
            recommended_state = "BLOCKED"
            safe_to_trade = False

        report = {
            "total_positions": total_positions,
            "odin_managed": odin_managed,
            "external_positions": external_positions,
            "orphan_positions": orphan_positions,
            "missing_positions": missing_positions,
            "unprotected_positions": unprotected_positions,
            "unknown_magic": unknown_magic,
            "recommended_state": recommended_state,
            "safe_to_trade": safe_to_trade,
            "ok": safe_to_trade,
            "reasons": reasons,
            "classes": classes,
        }

        self.log_reconciliation.write("mt5_reconciliation", report)
        return report

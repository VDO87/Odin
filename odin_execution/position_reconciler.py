from __future__ import annotations

from typing import Any

from odin_execution.position_registry import PositionClass, PositionRegistry


class PositionReconciler:
    def __init__(self, registry: PositionRegistry, *, odin_magic: int = 870087) -> None:
        self.registry = registry
        self.odin_magic = odin_magic

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
        classes = self.classify(mt5_positions)
        blockers = (
            len(classes[PositionClass.MISSING_POSITION.value])
            + len(classes[PositionClass.UNPROTECTED_POSITION.value])
            + len(classes[PositionClass.UNKNOWN_MAGIC.value])
            + len(classes[PositionClass.ORPHAN_POSITION.value])
        )
        return {
            "ok": blockers == 0,
            "blockers": blockers,
            "classes": classes,
        }

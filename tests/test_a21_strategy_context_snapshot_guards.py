import tempfile
import unittest
from pathlib import Path

from odin.core.bootstrap import validate_runtime
from odin.decision.strategy_context_snapshot import strategy_context_snapshot_status


class A21StrategyContextSnapshotGuardTests(unittest.TestCase):
    def test_runtime_contains_no_forbidden_operational_terms(self):
        text = _runtime_text()
        for term in (
            "metatrader5",
            "mt5.",
            "order" + "_send",
            "login(",
            "cred" + "entials",
            "buy" + "_signal",
            "sell" + "_signal",
            "entry" + "_price",
            "stop" + "_loss",
            "take" + "_profit",
            "position" + "_size",
            "send" + "_order",
            "place" + "_order",
            "execute" + "_order",
        ):
            self.assertNotIn(term, text)

    def test_snapshot_does_not_unlock_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            strategy_context_snapshot_status(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
            state = validate_runtime(
                log_path=str(root / "logs" / "events.jsonl"),
                sqlite_path=str(root / "runtime" / "odin.sqlite"),
            )
        self.assertIs(state["safe_to_trade"], False)
        self.assertIs(state["real_trading"], False)
        self.assertEqual(state["risk_state"], "READY_BLOCKING")


def _runtime_text() -> str:
    paths = (
        Path("src/odin/contracts/strategy_context_snapshot.py"),
        Path("src/odin/decision/strategy_context_snapshot.py"),
    )
    return "\n".join(path.read_text(encoding="utf-8").lower() for path in paths)


if __name__ == "__main__":
    unittest.main()

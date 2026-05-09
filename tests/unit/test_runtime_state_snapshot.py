from __future__ import annotations

import json
from pathlib import Path

from odin_control.system_controller import SystemController


def test_runtime_snapshot_file_created() -> None:
    controller = SystemController(log_root="logs")
    controller.execute("RUNTIME_RUN_ONCE", actor="test", role="system")

    path = Path("data/runtime/odin_state_snapshot.json")
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "runtime_state" in payload
    assert payload["trading_real_enabled"] is False
    assert payload["mt5_order_send_enabled"] is False

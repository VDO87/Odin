from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from odin_dashboard.demo_state import get_demo_state


ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_index_has_security_strip_and_command_bar() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_html.app", "--export-preview"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    body = (ROOT / "dashboard_preview" / "index.html").read_text(encoding="utf-8")

    assert "TRADING REAL: BLOCKED" in body
    assert "MT5 ORDER_SEND: BLOCKED" in body
    assert "BROKER REAL: BLOCKED" in body
    assert "ATLAS: SHADOW_ONLY" in body
    assert "LLM: READ_ONLY" in body
    assert "COMMAND BAR" in body
    assert "SPARKLINE" in body

    # Dangerous actions must not be rendered as dashboard controls.
    assert "ENABLE_REAL_TRADING" not in body
    assert "DIRECT_ORDER_SEND" not in body
    assert "MT5_CLOSE_POSITION" not in body


def test_demo_state_is_marked() -> None:
    state = get_demo_state()
    assert state.get("demo_data") is True

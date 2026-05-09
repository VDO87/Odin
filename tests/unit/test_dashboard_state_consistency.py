from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from odin_dashboard.state_provider import DashboardStateProvider


ROOT = Path(__file__).resolve().parents[2]


def test_state_provider_exposes_distinct_states() -> None:
    state = DashboardStateProvider(log_root="logs").load_state(force_demo=True)
    assert "runtime_state" in state
    assert "trading_permission_state" in state
    assert "system_health_state" in state
    assert "safe_to_trade" in state


def test_dashboard_shows_distinct_state_labels() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_html.app", "--export-preview"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    body = (ROOT / "dashboard_preview" / "index.html").read_text(encoding="utf-8")
    assert "Runtime State" in body
    assert "Trading Permission" in body
    assert "Health State" in body
    assert "safe_to_trade" in body

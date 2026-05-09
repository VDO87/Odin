from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from odin_dashboard.state_provider import DashboardStateProvider


ROOT = Path(__file__).resolve().parents[2]


def test_market_intelligence_exists_in_demo_state() -> None:
    provider = DashboardStateProvider(log_root="logs")
    state = provider.load_state(force_demo=True)
    panel = state.get("market_intelligence", {})
    assert isinstance(panel, dict)
    assert "news_status" in panel
    assert "macro_calendar_status" in panel
    assert "sentiment_summary" in panel


def test_market_intelligence_panel_is_present_on_index() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_html.app", "--export-preview"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    body = (ROOT / "dashboard_preview" / "index.html").read_text(encoding="utf-8")
    assert "Market Intelligence" in body
    assert "Sentiment" in body

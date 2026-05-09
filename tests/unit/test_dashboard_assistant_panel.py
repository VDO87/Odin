from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_assistant_panel_contains_quick_actions_and_safety_notice() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_html.app", "--export-preview"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    body = (ROOT / "dashboard_preview" / "index.html").read_text(encoding="utf-8")
    assert "Assistant / ODIN Chat" in body
    assert "Perguntar ao ODIN" in body
    assert "Estado" in body
    assert "Posso operar?" in body
    assert "LLM não executa comandos" in body

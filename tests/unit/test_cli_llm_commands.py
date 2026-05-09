from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "apps.dashboard_terminal.cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_llm_status_and_ask() -> None:
    assert _run("llm-status").returncode == 0
    assert _run("ask", "Qual é o estado do ODIN?").returncode == 0


def test_cli_blocks_dangerous_ask() -> None:
    result = _run("ask", "Activa trading real")
    assert result.returncode == 0
    assert "BLOCKED" in result.stdout or "bloqueado" in result.stdout.lower()


def test_cli_assistant_smoke_test() -> None:
    result = _run("assistant-smoke-test")
    assert result.returncode == 0
    assert "smoke_test" in result.stdout

from __future__ import annotations

import json
from pathlib import Path

import pytest

from odin_assistant.assistant_router import AssistantRouter
from odin_control.system_controller import SystemController


def test_assistant_answers_soak_questions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out_dir = tmp_path / "soak"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "latest_soak_result.json").write_text(
        json.dumps({"summary": {"result": "PASS", "total_cycles": 5, "no_order_attempts": True}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("ODIN_SOAK_TEST_OUTPUT_DIR", str(out_dir))

    controller = SystemController(log_root="logs")
    controller.execute("RUNTIME_RUN_ONCE", actor="test", role="system")
    assistant = AssistantRouter(controller)

    result1 = assistant.ask("Qual foi o último soak test?", channel="cli")
    result2 = assistant.ask("O ODIN está estável?", channel="cli")
    result3 = assistant.ask("Houve alguma tentativa de ordem?", channel="cli")

    assert "answer" in result1
    assert "answer" in result2
    assert "answer" in result3

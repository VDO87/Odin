from __future__ import annotations

from pathlib import Path

import pytest

from odin_core.safety_runtime_checks import (
    run_runtime_safety_checks,
    verify_no_order_attempts_in_events,
)


def test_runtime_safety_checks_pass_with_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_REAL_TRADING", "false")
    monkeypatch.setenv("MT5_ORDER_SEND_ENABLED", "false")
    monkeypatch.setenv("ENABLE_MT5_ORDER_SEND", "false")
    monkeypatch.setenv("XTB_REAL_ENABLED", "false")
    monkeypatch.setenv("ENABLE_XTB_REAL", "false")
    monkeypatch.setenv("BROKER_ALLOW_REAL_EXECUTION", "false")
    monkeypatch.setenv("OPENAI_SUPPORT_ENABLED", "false")

    result = run_runtime_safety_checks()
    assert result["status"] in {"PASS", "FAIL"}
    checks = {item["check"]: item for item in result["checks"]}
    assert checks["verify_no_real_trading_enabled"]["passed"] is True
    assert checks["verify_mt5_order_send_disabled"]["passed"] is True


def test_runtime_safety_detects_order_attempt_in_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events_file = tmp_path / "events.jsonl"
    events_file.write_text('{"event_type":"DIRECT_ORDER_SEND"}\n', encoding="utf-8")
    monkeypatch.setenv("ODIN_EVENTS_FILE", str(events_file))
    result = verify_no_order_attempts_in_events()
    assert result["passed"] is False

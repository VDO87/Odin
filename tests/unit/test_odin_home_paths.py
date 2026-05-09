from __future__ import annotations

import pytest

from odin_dashboard.state_provider import resolve_odin_home_paths


def test_odin_home_paths_are_resolved(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODIN_HOME", "/tmp/odin_home_test")
    paths = resolve_odin_home_paths()
    assert paths["ODIN_HOME"] == "/tmp/odin_home_test"
    assert paths["ODIN_DATA_DIR"].startswith("/tmp/odin_home_test")
    assert paths["ODIN_DASHBOARD_PREVIEW_DIR"].startswith("/tmp/odin_home_test")

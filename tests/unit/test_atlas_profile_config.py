from __future__ import annotations

import pytest

from odin_dashboard.state_provider import atlas_profile_status


def test_atlas_profile_lite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_PROFILE", "lite")
    profile = atlas_profile_status()
    assert profile["profile"] == "lite"
    assert profile["execution_permission"] == "SHADOW_ONLY"


def test_atlas_profile_full(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_PROFILE", "full")
    profile = atlas_profile_status()
    assert profile["profile"] == "full"
    assert profile["execution_permission"] == "SHADOW_ONLY"

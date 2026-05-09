from __future__ import annotations

from odin_dashboard.demo_state import get_demo_state


def test_demo_state_has_no_secrets_and_is_marked_demo() -> None:
    state = get_demo_state()
    text = str(state).lower()
    assert state.get("demo_data") is True
    assert "password" not in text
    assert "token" not in text
    assert "api_key" not in text

from __future__ import annotations

from pathlib import Path


def test_odin_trace_script_supports_verbose_and_filters_read_query_by_default() -> None:
    script = Path("scripts/odin_trace.sh").read_text(encoding="utf-8")

    assert "--verbose" in script
    assert "mode=operational (read_query hidden)" in script
    assert "mode=verbose (read_query visible)" in script
    assert 'event_type == "read_query" and not verbose' in script

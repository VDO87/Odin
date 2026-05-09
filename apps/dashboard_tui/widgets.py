from __future__ import annotations

from typing import Any

from odin_dashboard.formatters import sparkline


def badge(label: str, value: str) -> str:
    return f"[{label}] {value}"


def kv(label: str, value: Any) -> str:
    return f"{label:<22}: {value}"


def spark(values: list[float]) -> str:
    return sparkline(values)

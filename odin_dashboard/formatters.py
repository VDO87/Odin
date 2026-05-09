from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def short_ts(value: str | None) -> str:
    if not value:
        return "n/a"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%H:%M:%S")
    except ValueError:
        return str(value)


def sparkline(values: Iterable[float]) -> str:
    seq = list(values)
    if not seq:
        return ""
    lo = min(seq)
    hi = max(seq)
    if hi == lo:
        return _SPARK_CHARS[0] * len(seq)
    out = []
    for value in seq:
        norm = (value - lo) / (hi - lo)
        idx = round(norm * (len(_SPARK_CHARS) - 1))
        out.append(_SPARK_CHARS[idx])
    return "".join(out)


def compact_bool(flag: bool) -> str:
    return "YES" if flag else "NO"

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable


_SPARK_CHARS = "▁▂▃▄▅▆▇█"


CRITICAL_EVENTS = {
    "ERROR",
    "COMMAND_BLOCKED",
    "ORDER_ATTEMPT",
    "HEALTHCHECK_CRITICAL",
    "HEALTHCHECK_BLOCKED",
}


def short_ts(value: str | None) -> str:
    if not value:
        return "n/a"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%H:%M:%S")
    except ValueError:
        return str(value)


def heartbeat_age_seconds(value: str | None) -> int | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
    return max(0, int(delta.total_seconds()))


def normalize_price_series(values: Iterable[float | int | str]) -> list[float]:
    out: list[float] = []
    for raw in values:
        try:
            out.append(float(raw))
        except (TypeError, ValueError):
            continue
    return out


def render_ascii_sparkline(values: Iterable[float | int | str]) -> str:
    seq = normalize_price_series(values)
    if not seq:
        return "n/a"
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


def render_html_sparkline(values: Iterable[float | int | str]) -> str:
    ascii_line = render_ascii_sparkline(values)
    return f'<span class="sparkline" aria-label="market-sparkline">{ascii_line}</span>'


def sparkline(values: Iterable[float | int | str]) -> str:
    return render_ascii_sparkline(values)


def compact_bool(flag: bool) -> str:
    return "YES" if flag else "NO"


def _extract_event_fields(event: dict[str, Any]) -> tuple[str, str, str]:
    raw_type = event.get("event_type", event.get("event", "EVENT"))
    event_type = str(raw_type)
    message = str(event.get("message", event.get("reason", "")))
    if not message and isinstance(event.get("data"), dict):
        data = event["data"]
        message = str(data.get("reason", data.get("command", "")))
    timestamp = str(event.get("timestamp", ""))
    return event_type, message, timestamp


def group_repeated_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: list[dict[str, Any]] = []
    prev_key: tuple[str, str] | None = None

    for event in events:
        if not isinstance(event, dict):
            continue
        event_type, message, timestamp = _extract_event_fields(event)
        key = (event_type, message)
        critical = event_type in CRITICAL_EVENTS

        if (
            not critical
            and grouped
            and prev_key == key
            and not grouped[-1].get("critical", False)
        ):
            grouped[-1]["count"] = int(grouped[-1].get("count", 1)) + 1
            grouped[-1]["last_timestamp"] = timestamp
            continue

        grouped.append(
            {
                "event_type": event_type,
                "message": message,
                "timestamp": timestamp,
                "last_timestamp": timestamp,
                "count": 1,
                "critical": critical,
            }
        )
        prev_key = key

    return grouped

from __future__ import annotations

import re
from typing import Any


_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|token|password|secret|telegram_bot_token|openai_api_key|xtb_password|mt5_password|ibkr|login)"
)
_ENV_ASSIGNMENT_PATTERN = re.compile(r"(?P<k>[A-Z0-9_]{3,})=(?P<v>[^\s]+)")
_LONG_SECRET_PATTERN = re.compile(r"\b[A-Za-z0-9_\-]{24,}\b")
_OPENAI_KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9]{8,}\b")


REDACTED = "***REDACTED***"


def _redact_text(value: str) -> str:
    def replace_assignment(match: re.Match[str]) -> str:
        key = match.group("k")
        if _SENSITIVE_KEY_PATTERN.search(key):
            return f"{key}={REDACTED}"
        return match.group(0)

    text = _ENV_ASSIGNMENT_PATTERN.sub(replace_assignment, value)
    text = _OPENAI_KEY_PATTERN.sub(REDACTED, text)

    words: list[str] = []
    for token in text.split():
        if _LONG_SECRET_PATTERN.fullmatch(token) and any(c.isdigit() for c in token):
            words.append(REDACTED)
        else:
            words.append(token)
    return " ".join(words)


def redact_sensitive_data(payload: Any, *, parent_key: str = "") -> Any:
    if isinstance(payload, dict):
        clean: dict[str, Any] = {}
        for key, value in payload.items():
            key_str = str(key)
            if _SENSITIVE_KEY_PATTERN.search(key_str):
                clean[key_str] = REDACTED
            else:
                clean[key_str] = redact_sensitive_data(value, parent_key=key_str)
        return clean

    if isinstance(payload, list):
        return [redact_sensitive_data(item, parent_key=parent_key) for item in payload]

    if isinstance(payload, tuple):
        return tuple(redact_sensitive_data(item, parent_key=parent_key) for item in payload)

    if isinstance(payload, str):
        if _SENSITIVE_KEY_PATTERN.search(parent_key):
            return REDACTED
        return _redact_text(payload)

    return payload

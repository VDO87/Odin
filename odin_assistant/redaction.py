from __future__ import annotations

from typing import Any

from odin_logs.redaction import redact_sensitive_data


def redact_for_assistant(payload: Any) -> Any:
    return redact_sensitive_data(payload)

from __future__ import annotations

from odin_assistant.redaction import redact_for_assistant


def test_redaction_masks_sensitive_values() -> None:
    payload = {
        "OPENAI_API_KEY": "sk-1234567890abcdef",
        "TELEGRAM_BOT_TOKEN": "123456:abcdef",
        "safe": "ok",
        "nested": {"MT5_PASSWORD": "secret-pass"},
    }
    redacted = redact_for_assistant(payload)
    assert redacted["OPENAI_API_KEY"] == "***REDACTED***"
    assert redacted["TELEGRAM_BOT_TOKEN"] == "***REDACTED***"
    assert redacted["nested"]["MT5_PASSWORD"] == "***REDACTED***"
    assert redacted["safe"] == "ok"

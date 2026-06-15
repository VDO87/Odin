"""State factory for A1."""

from odin.contracts.state import OdinState, off_safe_state


def build_safe_state(*, sqlite_initialized: bool, jsonl_logger_ready: bool) -> OdinState:
    return off_safe_state(
        sqlite_initialized=sqlite_initialized,
        jsonl_logger_ready=jsonl_logger_ready,
    )


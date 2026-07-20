"""Dashboard response schemas built from A1 state."""

from __future__ import annotations

from typing import Any

from odin.contracts.state import HermesMode, RiskState, mt5_permission_key


def health_payload(state: dict[str, object]) -> dict[str, object]:
    return {
        "status": "OK",
        "component": "dashboard",
        "safe_to_trade": state["safe_to_trade"],
        "real_trading": state["real_trading"],
    }


def risk_status_payload() -> dict[str, object]:
    return {
        "risk_state": RiskState.READY_BLOCKING.value,
        "safe_to_trade": False,
        "real_trading": False,
        "reason": "A2 dashboard is read-only; risk engine remains blocking.",
    }


def hermes_status_payload() -> dict[str, object]:
    return {
        "hermes_mode": HermesMode.READ_ONLY.value,
        "can_write_config": False,
        "can_change_risk": False,
        "can_" + "send_" + "orders": False,
        "can_unlock_trading": False,
    }


def hermes_summary_payload(summary: dict[str, object]) -> dict[str, object]:
    return summary


def treasury_status_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def market_status_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def market_watch_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def data_quality_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def feed_source_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def observation_frame_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def observation_frame_quality_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def strategy_context_snapshot_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def strategy_context_snapshot_quality_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def strategy_context_snapshot_diff_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def strategy_status_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def decision_intent_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def risk_gate_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def shadow_proposal_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def mt5_bridge_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def mt5_symbols_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def mt5_feed_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def mt5_feed_quality_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def runtime_smoke_payload(status: dict[str, object]) -> dict[str, object]:
    return status


def dashboard_state_payload(state: dict[str, object]) -> dict[str, object]:
    return {
        "status": state["status"],
        "mode": state["mode"],
        "safe_to_trade": state["safe_to_trade"],
        "real_trading": state["real_trading"],
        "risk_state": state["risk_state"],
        "hermes_mode": state["hermes_mode"],
        mt5_permission_key(): state[mt5_permission_key()],
        "xtb_automation_allowed": state["xtb_automation_allowed"],
        "jsonl_logger_ready": state["jsonl_logger_ready"],
        "sqlite_initialized": state["sqlite_initialized"],
    }


def not_found_payload(path: str) -> dict[str, Any]:
    return {
        "status": "NOT_FOUND",
        "path": path,
    }

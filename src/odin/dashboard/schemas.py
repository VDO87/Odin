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


def hermes_runtime_payload(summary: dict[str, object]) -> dict[str, object]:
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


def operational_overview_payload(
    *,
    state: dict[str, object],
    hermes: dict[str, object],
    market: dict[str, object],
    observation: dict[str, object],
    strategy: dict[str, object],
    risk: dict[str, object],
    observer: dict[str, object],
    mt5: dict[str, object],
    mt5_observation: dict[str, object],
) -> dict[str, object]:
    """Stable read-only summary for a human operator dashboard.

    This endpoint deliberately presents controls and observations together but
    never accepts configuration, provider, strategy, or execution input.
    """
    return {
        "status": "OK",
        "component": "operations_overview",
        "mode": "LOCAL_ONLY",
        "read_only": True,
        "safety": {
            "safe_to_trade": False,
            "real_trading": False,
            "execution_allowed": False,
            "human_approval_required": True,
            "dashboard_configuration_writes_allowed": False,
        },
        "local_runtime": {
            "runtime_status": state["status"],
            "hermes_status": hermes["status"],
            "hermes_operational_state": hermes["operational_state"],
            "ollama_available": hermes["local_provider"]["ollama_available"],
            "local_models": hermes["local_provider"]["models"],
            "resource_guardian": hermes["resource_guardian"],
            "warnings": hermes["warnings"],
        },
        "observation": {
            "market_status": market["status"],
            "market_provider": market.get("provider", "market_data_mock"),
            "observation_frame_status": observation["status"],
            "strategy_status": strategy["status"],
            "risk_gate_status": risk["status"],
        },
        "supervised_demo": {
            "observer": {
                "status": observer["status"],
                "reason": observer["reason"],
                "execution_allowed": observer["execution_allowed"],
            },
            "mt5": {
                "status": mt5["status"],
                "reason": mt5.get("reason", "demo_preparation_pending_operator_review"),
                "terminal_connection_attempted": mt5["terminal_connection_attempted"],
                "kill_switch_engaged": mt5.get("kill_switch_engaged", False),
                "execution_allowed": mt5["execution_allowed"],
            },
            "mt5_observation": {
                "status": mt5_observation["status"],
                "as_of": mt5_observation.get("as_of", ""),
                "market_status": mt5_observation.get("market", {}).get("status", "UNKNOWN") if isinstance(mt5_observation.get("market"), dict) else "UNKNOWN",
                "market_as_of": mt5_observation.get("market", {}).get("as_of", "") if isinstance(mt5_observation.get("market"), dict) else "",
                "positions_count": len(mt5_observation.get("positions", [])) if isinstance(mt5_observation.get("positions"), list) else 0,
                "execution_allowed": False,
            },
        },
        "configuration": {
            "provider_policy": "local_first",
            "cloud_fallback_allowed": False,
            "automatic_code_application": False,
            "repository_code_application": False,
            "financial_data_policy": "read_only_observation",
            "changes": "Use a reviewed local config change; this endpoint is informational.",
        },
    }


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

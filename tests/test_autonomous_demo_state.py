from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest

from odin.dashboard.routes import DashboardRoutes
from odin.trading.autonomous_demo_state import (
    ALLOWED_STATES,
    append_incident,
    append_repair_evidence,
    build_supervisor_state,
    read_control,
    read_state,
    request_control,
    validate_state,
    write_heartbeat,
    write_state,
)


NOW = datetime(2026, 8, 29, 12, tzinfo=UTC)


@pytest.mark.parametrize("state", sorted(ALLOWED_STATES))
def test_every_documented_supervisor_state_is_durable_and_disarmed(
    tmp_path: Path, state: str
) -> None:
    path = tmp_path / "state.json"
    value = build_supervisor_state(
        state,
        cycle=7,
        reason_codes=["fixture"],
        observed={"broker": "OANDA TMS Brokers S.A.", "password": "must disappear"},
        now_utc=NOW,
    )
    write_state(path, value)
    loaded = read_state(path)

    assert loaded["state"] == state
    assert loaded["observed"]["broker"] == "OANDA TMS Brokers S.A."
    assert "password" not in loaded["observed"]
    assert loaded["safe_to_trade"] is False
    assert loaded["real_trading"] is False
    assert loaded["execution_allowed"] is False


def test_state_tampering_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    value = build_supervisor_state("MONITOR_ONLY", cycle=1, now_utc=NOW)
    write_state(path, value)
    value["state"] = "ACCEPTANCE_PASSED"
    path.write_text(json.dumps(value), encoding="utf-8")

    loaded = read_state(path)

    assert loaded["status"] == "BLOCKED"
    assert loaded["state"] == "EXECUTION_PAUSED"
    assert validate_state(value) is False


def test_heartbeat_and_incident_memory_are_non_secret(tmp_path: Path) -> None:
    heartbeat = write_heartbeat(
        tmp_path / "heartbeat.json",
        cycle=2,
        state="WAITING_MARKET",
        process_id=123,
        started_at_utc=NOW.isoformat(),
        next_check_at_utc=NOW.isoformat(),
        now_utc=NOW,
    )
    incident = append_incident(
        tmp_path / "incidents.jsonl",
        incident_type="MT5_DISCONNECTED",
        component="mt5",
        error_code="-10005",
        root_cause="ipc_timeout",
        evidence={"server": "OANDATMS-MT5", "token": "must disappear"},
        repair_attempts=1,
        successful_fix="bounded_reconnect",
        repair_files=["scripts/reconnect.py", "token-secret.txt"],
        repair_tests=["test_reconnect", "credential probe"],
        state_before="RECOVERING",
        state_after="MONITOR_ONLY",
        now_utc=NOW,
    )

    assert heartbeat["state"] == "WAITING_MARKET"
    assert heartbeat["execution_allowed"] is False
    assert len(incident["fingerprint"]) == 64
    assert incident["repair_files"] == ["scripts/reconnect.py", "REDACTED"]
    assert incident["repair_tests"] == ["test_reconnect", "REDACTED"]
    assert incident["state_before"] == "RECOVERING"
    assert incident["state_after"] == "MONITOR_ONLY"
    assert "must disappear" not in (tmp_path / "incidents.jsonl").read_text()
    assert "token-secret" not in (tmp_path / "incidents.jsonl").read_text()
    assert "credential probe" not in (tmp_path / "incidents.jsonl").read_text()


def test_incident_fingerprint_accumulates_occurrences_without_new_diagnosis(
    tmp_path: Path,
) -> None:
    path = tmp_path / "incidents.jsonl"
    first = append_incident(
        path,
        incident_type="MT5_DISCONNECTED",
        component="mt5",
        error_code="-10005",
        root_cause="ipc_timeout",
        evidence={"status": "offline"},
        now_utc=NOW,
    )
    second = append_incident(
        path,
        incident_type="MT5_DISCONNECTED",
        component="mt5",
        error_code="-10005",
        root_cause="ipc_timeout",
        evidence={"status": "offline"},
        now_utc=NOW + timedelta(minutes=1),
    )

    assert first["fingerprint"] == second["fingerprint"]
    assert second["occurrences"] == 2
    assert second["first_seen"] == first["first_seen"]
    assert first["regression_status"] == "NEW"
    assert second["regression_status"] == "RECURRING"

    annotation = append_repair_evidence(
        path,
        fingerprint=str(second["fingerprint"]),
        successful_fix="bounded_reconnect",
        repair_attempts=2,
        repair_files=["scripts/reconnect.py"],
        repair_tests=["test_reconnect"],
        state_before="RECOVERING",
        state_after="MONITOR_ONLY",
        checkpoint="abc1234",
        now_utc=NOW + timedelta(minutes=2),
    )

    assert annotation["occurrences"] == 2
    assert annotation["last_seen"] == second["last_seen"]
    assert annotation["repair_annotation"] is True
    assert annotation["repair_annotated_at"] == (NOW + timedelta(minutes=2)).isoformat()
    assert annotation["successful_fix"] == "bounded_reconnect"

    regression = append_incident(
        path,
        incident_type="MT5_DISCONNECTED",
        component="mt5",
        error_code="-10005",
        root_cause="ipc_timeout",
        evidence={"status": "offline"},
        now_utc=NOW + timedelta(minutes=3),
    )

    assert regression["occurrences"] == 3
    assert regression["regression_status"] == "REGRESSION"
    assert regression["successful_fix"] == "bounded_reconnect"


def test_operator_control_fails_to_pause_and_never_enables_global_execution(
    tmp_path: Path,
) -> None:
    path = tmp_path / "control.json"
    assert read_control(path)["action"] == "PAUSE"
    path.write_text(
        json.dumps(
            {
                "action": "RESUME",
                "request_id": "operator-1",
                "requested_at_utc": NOW.isoformat(),
                "execution_allowed": True,
            }
        ),
        encoding="utf-8",
    )

    loaded = read_control(path)

    assert loaded == {
        "action": "RESUME",
        "request_id": "operator-1",
        "requested_at_utc": NOW.isoformat(),
    }


def test_unknown_state_is_rejected() -> None:
    with pytest.raises(ValueError, match="autonomous_demo_state_invalid"):
        build_supervisor_state("TRADING_REAL", cycle=0)


def test_resume_requires_visual_confirmation_and_remains_a_revalidation_request(
    tmp_path: Path,
) -> None:
    path = tmp_path / "control.json"
    blocked = request_control(
        path, action="RESUME", request_id="r1", resume_confirmed=False, now_utc=NOW
    )
    accepted = request_control(
        path, action="RESUME", request_id="r2", resume_confirmed=True, now_utc=NOW
    )

    assert blocked["status"] == "BLOCKED"
    assert not path.exists() or read_control(path).get("request_id") != "r1"
    assert accepted["status"] == "ACCEPTED"
    assert accepted["resume_requires_full_gate_revalidation"] is True
    assert accepted["execution_allowed"] is False


def test_dashboard_exposes_state_and_operator_controls_without_broker_capability(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    heartbeat_path = tmp_path / "heartbeat.json"
    control_path = tmp_path / "control.json"
    incidents_path = tmp_path / "incidents.jsonl"
    write_state(
        state_path,
        build_supervisor_state(
            "MONITOR_ONLY",
            cycle=4,
            now_utc=NOW,
            observed={
                "balance": 50_000.0,
                "logical_symbol": "EURUSD",
                "broker_symbol": "EURUSD.pro",
                "data_freshness": "FRESH",
                "spread_pips": 1.2,
                "spread_limit_points": 30.0,
                "floating_pnl": -0.25,
                "drawdown_percent": 0.01,
                "latest_decision": {"signal": "NO_TRADE"},
            },
        ),
    )
    write_heartbeat(
        heartbeat_path,
        cycle=4,
        state="MONITOR_ONLY",
        process_id=10,
        started_at_utc=NOW.isoformat(),
        next_check_at_utc=NOW.isoformat(),
        now_utc=NOW,
    )
    routes = DashboardRoutes(
        log_path=str(tmp_path / "events.jsonl"),
        sqlite_path=str(tmp_path / "events.sqlite"),
        autonomous_state_path=str(state_path),
        autonomous_heartbeat_path=str(heartbeat_path),
        autonomous_control_path=str(control_path),
        autonomous_incidents_path=str(incidents_path),
        autonomous_report_root=str(tmp_path / "reports"),
    )

    status, payload = routes.serve("/operations/autonomous-demo")
    resume_status, resume = routes.configure_autonomous_demo_control(
        {"action": "RESUME", "resume_confirmed": False}
    )
    pause_status, pause = routes.configure_autonomous_demo_control({"action": "PAUSE"})

    assert status == 200
    assert payload["supervisor"]["state"] == "MONITOR_ONLY"
    assert payload["heartbeat"]["started_at_utc"] == NOW.isoformat()
    assert payload["financial"]["balance"] == 50_000.0
    assert payload["market"]["logical_symbol"] == "EURUSD"
    assert payload["market"]["spread_pips"] == 1.2
    assert payload["financial"]["floating_pnl"] == -0.25
    assert payload["decision"]["signal"] == "NO_TRADE"
    assert payload["execution_allowed"] is False
    assert resume_status == 400
    assert resume["reason"] == "resume_visual_confirmation_required"
    assert pause_status == 200
    assert pause["status"] == "ACCEPTED"
    assert pause["execution_allowed"] is False

from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _attribute_calls(path: Path, attribute: str) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attribute
    ]


def test_rc2_config_is_strictly_limited_and_globally_disarmed() -> None:
    config = json.loads((ROOT / "config/demo_execution_rc2.json").read_text())

    assert config["broker"] == "OANDA TMS Brokers S.A."
    assert config["server"] == "OANDATMS-MT5"
    assert config["terminal_path"] == r"C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe"
    assert config["logical_symbol"] == "EURUSD"
    assert config["broker_symbol"] == "EURUSD.pro"
    assert config["fixed_volume"] == 0.01
    assert config["max_simultaneous_positions"] == 1
    assert config["max_simultaneous_orders"] == 1
    assert config["max_completed_trades_per_day"] == 3
    assert config["max_daily_demo_loss_eur"] == 5.0
    assert config["fallback_allowed"] is False
    assert r"D:\ODIN_LOCAL\mt5\terminal64.exe" in config["excluded_terminal_paths"]
    assert config["safe_to_trade"] is False
    assert config["real_trading"] is False
    assert config["execution_allowed"] is False


def test_persistent_supervisor_has_no_direct_financial_submission() -> None:
    supervisor = ROOT / "scripts/windows/mt5_autonomous_demo_supervisor.py"
    source = supervisor.read_text(encoding="utf-8")

    assert _attribute_calls(supervisor, "order_send") == []
    assert "C:\\Program Files\\OANDA TMS MT5 Terminal\\terminal64.exe" in source
    assert "D:\\ODIN_LOCAL\\mt5\\terminal64.exe" in source
    assert "CreateMutexW" in source
    assert "copy_rates_from_pos" in source
    assert "positions_get" in source
    assert "orders_get" in source
    assert "recovery_gate" in source
    assert "broker_submission_called" in source
    assert "run_autonomous_demo_order" in source
    assert "completed_reconciled_lifecycle" in source
    assert "demo_decision_already_recorded" in source
    assert "daily_broker_history_unavailable" in source
    assert "reconcile_latest_broker_close" in source
    assert "update_autonomous_demo_reports" in source
    assert "previous_request_id" in source
    assert "current_request_id != previous_request_id" in source
    assert 'incident_type="RESOURCE_GUARD_BLOCK"' in source
    assert 'observation["resources"] = _resource_gate()' in source


def test_resource_block_pauses_execution_before_any_decision() -> None:
    supervisor = ROOT / "scripts/windows/mt5_autonomous_demo_supervisor.py"
    tree = ast.parse(supervisor.read_text(encoding="utf-8"))
    classify = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_classify_state"
    )
    namespace: dict[str, object] = {}
    exec(compile(ast.Module(body=[classify], type_ignores=[]), str(supervisor), "exec"), namespace)

    state, reasons = namespace["_classify_state"](
        {
            "status": "OK",
            "resources": {
                "status": "BLOCK",
                "reason_codes": ["thermal_guardrail_exceeded"],
            },
        },
        {"action": "RESUME"},
    )

    assert state == "EXECUTION_PAUSED"
    assert reasons == ["thermal_guardrail_exceeded"]


def test_only_isolated_adapter_still_contains_one_order_send_call() -> None:
    calls: list[tuple[Path, int]] = []
    for root in (ROOT / "src", ROOT / "scripts"):
        for path in root.rglob("*.py"):
            calls.extend((path, line) for line in _attribute_calls(path, "order_send"))

    assert len(calls) == 1
    assert calls[0][0] == ROOT / "src/odin/adapters/mt5/demo_execution_adapter.py"


def test_task_is_user_scoped_single_instance_and_bounded_restart() -> None:
    installer = (ROOT / "scripts/windows/Install-ODIN-Autonomous-Demo-RC2-Task.ps1").read_text(
        encoding="utf-8"
    )
    launcher = (ROOT / "scripts/windows/Start-ODIN-Autonomous-Demo-RC2.ps1").read_text(
        encoding="utf-8"
    )

    assert "-AtLogOn" in installer
    assert "-RunLevel Limited" in installer
    assert "-LogonType Interactive" in installer
    assert "-MultipleInstances IgnoreNew" in installer
    assert "-RestartCount 3" in installer
    assert "-ExecutionTimeLimit ([TimeSpan]::Zero)" in installer
    assert '[string]$WorkingDirectory = "D:\\ODIN_LOCAL"' in installer
    assert "Copy-Item -LiteralPath $launcher -Destination $installedLauncher -Force" in installer
    assert "installedDashboardLauncher" in installer
    assert 'New-ScheduledTaskAction -Execute "cmd.exe"' in installer
    assert 'replace "`r?`n", "`r`n"' in installer
    wrapper = (ROOT / "scripts/windows/Start-ODIN-Autonomous-Demo-RC2.cmd").read_text(
        encoding="utf-8"
    )
    assert "-NonInteractive" in wrapper
    assert "ODIN_RC2_EXIT" in wrapper
    dashboard_launcher = (ROOT / "scripts/windows/Start-ODIN-Dashboard-Persistent.ps1").read_text(
        encoding="utf-8"
    )
    assert "/home/odin/projects/odin/scripts/run_dashboard_local.sh" in dashboard_launcher
    assert '"43200"' in dashboard_launcher
    assert "installed launcher hash mismatch" in installer
    assert "ODIN_OANDA_PASSWORD" not in installer + launcher
    assert r"C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe" in launcher
    assert r"D:\ODIN_LOCAL\mt5\terminal64.exe" in launcher
    assert "wsl.exe -d Ubuntu-ODIN --user odin --exec git" in launcher
    assert "ODIN_RUNTIME_RATIONALIZATION_REPORT.md" in launcher
    assert "Copy-Item -LiteralPath $rationalizationSource" in launcher
    assert "& $PythonPath $probe" in launcher
    assert "Start-Process -FilePath $PythonPath" not in launcher


def test_safe_stop_and_pause_controls_do_not_stop_observability() -> None:
    control = (ROOT / "scripts/windows/Set-ODIN-Autonomous-Demo-Control.ps1").read_text(
        encoding="utf-8"
    )

    assert "PAUSE" in control
    assert "SAFE_STOP" in control
    assert "RESUME" in control
    assert "ConfirmResume" in control
    assert "Stop-ScheduledTask" not in control
    assert "execution_allowed = $false" in control
    assert "real_trading = $false" in control
    assert "[Text.UTF8Encoding]::new($false)" in control


def test_bounded_sleep_never_passes_negative_time_after_deadline_race() -> None:
    supervisor = ROOT / "scripts/windows/mt5_autonomous_demo_supervisor.py"
    tree = ast.parse(supervisor.read_text(encoding="utf-8"))
    sleep_function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_sleep_bounded"
    )

    class AdvancingClock:
        def __init__(self) -> None:
            self.values = iter((100.0, 100.5, 101.1))
            self.sleeps: list[float] = []

        def monotonic(self) -> float:
            return next(self.values)

        def sleep(self, seconds: float) -> None:
            assert seconds >= 0
            self.sleeps.append(seconds)

    clock = AdvancingClock()
    namespace = {
        "Path": Path,
        "STOP_REQUESTED": False,
        "read_control": lambda _path: {},
        "time": clock,
    }
    exec(compile(ast.Module(body=[sleep_function], type_ignores=[]), str(supervisor), "exec"), namespace)

    namespace["_sleep_bounded"](
        1,
        control_path=Path("unused.json"),
        previous_request_id="",
    )

    assert clock.sleeps == []

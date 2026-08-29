from __future__ import annotations

import ast
import hashlib
import importlib.util
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
    assert "run_next_hermes_reality_analysis" in source
    assert "HERMES_REALITY_ANALYSIS_EXCEPTION" in source
    assert "previous_request_id" in source
    assert "current_request_id != previous_request_id" in source
    assert 'incident_type="RESOURCE_GUARD_BLOCK"' in source
    assert 'observation["resources"] = _resource_gate(' in source
    assert 'dashboard_status=str(observation.get("dashboard", ""))' in source
    assert "_merge_wsl_runtime_evidence" in source
    assert '"wsl_runtime_evidence"] = "odin_dashboard_healthcheck"' in source
    assert 'Path(os.environ["ODIN_RC2_RESOURCE_PROBE_PATH"])' in source
    assert "get_odin_autonomous_demo_resources.py" in source
    assert 'sys.executable,' in source
    assert '"--supervisor-process-id"' in source
    assert '"probe_duration_ms"' in source
    assert "HERMES:1" in source
    assert "[h]ermes_cli" in source
    assert 'wsl_snapshot.get("wsl_hermes_running") is True' in source
    assert '"resource_probe_timeout"' in source
    assert '"resource_probe_invalid_json"' in source
    assert "RESOURCE_PROBE_TIMEOUT_SECONDS = 45" in source
    assert "timeout=RESOURCE_PROBE_TIMEOUT_SECONDS" in source
    assert "WSL_RESOURCE_PROBE_TIMEOUT_SECONDS = 10" in source
    assert source.count("creationflags=subprocess.CREATE_NO_WINDOW") >= 2
    assert "parse_wsl_resource_snapshot" in source
    assert 'incident_type="DASHBOARD_RECOVERY"' in source
    assert "dashboard_restarted_by_bounded_launcher" in source
    assert "DASHBOARD_UNAVAILABLE" in source
    assert "DASHBOARD_RUNNING" in source
    assert "_bootstrap_runtime_environment()" in source
    assert "_VENV_SITE_PACKAGES" in source


def test_wsl_timeout_uses_only_current_odin_dashboard_health_as_runtime_evidence() -> None:
    supervisor = ROOT / "scripts/windows/mt5_autonomous_demo_supervisor.py"
    tree = ast.parse(supervisor.read_text(encoding="utf-8"))
    merge = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_merge_wsl_runtime_evidence"
    )
    namespace: dict[str, object] = {}
    exec(
        compile(ast.Module(body=[merge], type_ignores=[]), str(supervisor), "exec"),
        namespace,
    )
    merge_evidence = namespace["_merge_wsl_runtime_evidence"]
    timeout = {
        "wsl_running": False,
        "wsl_probe_error_code": "wsl_resource_probe_timeout",
    }

    healthy = merge_evidence(timeout, dashboard_status="RUNNING")
    offline = merge_evidence(timeout, dashboard_status="RECOVERY_FAILED")

    assert healthy == {
        "wsl_running": True,
        "wsl_probe_error_code": "wsl_resource_probe_timeout",
        "wsl_runtime_evidence": "odin_dashboard_healthcheck",
        "wsl_telemetry_degraded": True,
    }
    assert offline == timeout


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


def test_resource_probe_failure_diagnostic_is_bounded_and_never_stores_raw_output() -> None:
    supervisor = ROOT / "scripts/windows/mt5_autonomous_demo_supervisor.py"
    tree = ast.parse(supervisor.read_text(encoding="utf-8"))
    diagnostic = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_resource_probe_failure"
    )

    class Clock:
        @staticmethod
        def monotonic() -> float:
            return 12.25

    namespace = {"hashlib": hashlib, "time": Clock}
    exec(
        compile(ast.Module(body=[diagnostic], type_ignores=[]), str(supervisor), "exec"),
        namespace,
    )
    result = namespace["_resource_probe_failure"](
        "resource_probe_exit_nonzero",
        started=10.0,
        exit_code=1,
        output="sensitive diagnostic must not persist",
    )

    assert result["probe_status"] == "BLOCKED"
    assert result["probe_error_code"] == "resource_probe_exit_nonzero"
    assert result["probe_duration_ms"] == 2250
    assert result["probe_exit_code"] == 1
    assert result["probe_output_bytes"] == 37
    assert len(result["probe_output_sha256"]) == 64
    assert "sensitive" not in json.dumps(result)


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
    assert "installedResourceProbe" in installer
    assert "resourceProbeInstalledHash" in installer
    assert "New-ScheduledTaskAction -Execute $basePython" in installer
    assert "mt5_autonomous_demo_bootstrap.py" in installer
    assert "--runtime-root" in installer
    assert "--canonical-repo-root" in installer
    assert '$arguments = "`"$installedBootstrap`"' in installer
    assert "runtime-manifest.json" in installer
    assert "contains_environment_file = $false" in installer
    assert "versioned runtime hash mismatch" in installer
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
    assert "wsl.exe -d Ubuntu-ODIN --user odin --exec git" not in launcher
    assert "ODIN_RUNTIME_RATIONALIZATION_REPORT.md" in launcher
    assert "Copy-Item -LiteralPath $rationalizationSource" in launcher
    assert "& $basePython $probe" in launcher
    assert "Start-Process -FilePath $PythonPath" not in launcher
    assert "ODIN_RC2_RESOURCE_PROBE_PATH" in launcher
    resource_probe = (
        ROOT / "scripts/windows/Get-ODIN-Autonomous-Demo-Resources.ps1"
    ).read_text(encoding="utf-8")
    python_resource_probe = ROOT / "scripts/windows/get_odin_autonomous_demo_resources.py"
    supervisor_source = (
        ROOT / "scripts/windows/mt5_autonomous_demo_supervisor.py"
    ).read_text(encoding="utf-8")
    assert "wsl.exe" not in resource_probe
    assert _attribute_calls(python_resource_probe, "order_send") == []
    python_probe_source = python_resource_probe.read_text(encoding="utf-8")
    assert "GlobalMemoryStatusEx" in python_probe_source
    assert "GetSystemTimes" in python_probe_source
    assert "OpenMutexW" in python_probe_source
    assert "CreateToolhelp32Snapshot" in python_probe_source
    assert '"hermes.exe"' in python_probe_source
    assert '"ollama.exe"' in python_probe_source
    assert 'timeout=20' in python_probe_source
    assert "tasklist.exe" not in python_probe_source
    assert "ulimit -n; ps -e --no-headers | wc -l; free -b" in supervisor_source


def test_local_runtime_bootstrap_is_non_financial_and_uses_versioned_sources() -> None:
    bootstrap = ROOT / "scripts/windows/mt5_autonomous_demo_bootstrap.py"
    source = bootstrap.read_text(encoding="utf-8")

    assert _attribute_calls(bootstrap, "order_send") == []
    assert "ODIN_RC2_CANONICAL_REPO_ROOT" in source
    assert "ODIN_RC2_REPO_SRC" in source
    assert "ODIN_RC2_WINDOWS_SCRIPTS" in source
    assert "ODIN_RC1_REPO_SRC" in source
    assert "rc2_installed_runtime_root_mismatch" in source
    assert "RESTART_DELAYS_SECONDS = (5, 30, 60)" in source
    assert "SUPERVISOR_RESTART_SCHEDULED" in source
    assert "SUPERVISOR_RESTART_BUDGET_EXHAUSTED" in source
    assert "broker_submission_called" in source


def test_local_runtime_watchdog_restarts_once_then_preserves_clean_exit() -> None:
    bootstrap = ROOT / "scripts/windows/mt5_autonomous_demo_bootstrap.py"
    specification = importlib.util.spec_from_file_location("rc2_bootstrap", bootstrap)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return_codes = iter((-1, 0))
    processes: list[object] = []
    sleeps: list[float] = []
    events: list[dict[str, object]] = []

    class Process:
        def __init__(self, return_code: int) -> None:
            self.pid = 100 + len(processes)
            self.return_code = return_code

        def wait(self) -> int:
            return self.return_code

    def popen(_command: list[str], **_kwargs: object) -> Process:
        process = Process(next(return_codes))
        processes.append(process)
        return process

    result = module._supervise(
        ["python", "supervisor.py"],
        popen=popen,
        sleep=sleeps.append,
        record=events.append,
    )

    assert result == 0
    assert len(processes) == 2
    assert sleeps == [5]
    assert [event["event"] for event in events] == [
        "SUPERVISOR_RESTART_SCHEDULED",
        "SUPERVISOR_EXITED_CLEANLY",
    ]
    assert all(event["broker_submission_called"] is False for event in events)


def test_local_runtime_watchdog_exhausts_bounded_restart_budget() -> None:
    bootstrap = ROOT / "scripts/windows/mt5_autonomous_demo_bootstrap.py"
    specification = importlib.util.spec_from_file_location("rc2_bootstrap_exhausted", bootstrap)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    processes: list[object] = []
    sleeps: list[float] = []
    events: list[dict[str, object]] = []

    class Process:
        pid = 200

        @staticmethod
        def wait() -> int:
            return 17

    def popen(_command: list[str], **_kwargs: object) -> Process:
        process = Process()
        processes.append(process)
        return process

    result = module._supervise(
        ["python", "supervisor.py"],
        popen=popen,
        sleep=sleeps.append,
        record=events.append,
    )

    assert result == 17
    assert len(processes) == 4
    assert sleeps == [5, 30, 60]
    assert events[-1]["event"] == "SUPERVISOR_RESTART_BUDGET_EXHAUSTED"


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

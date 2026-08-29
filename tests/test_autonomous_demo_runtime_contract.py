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


def test_only_isolated_adapter_still_contains_one_order_send_call() -> None:
    calls: list[tuple[Path, int]] = []
    for root in (ROOT / "src", ROOT / "scripts"):
        for path in root.rglob("*.py"):
            calls.extend((path, line) for line in _attribute_calls(path, "order_send"))

    assert len(calls) == 1
    assert calls[0][0] == ROOT / "src/odin/adapters/mt5/demo_execution_adapter.py"


def test_task_is_user_scoped_single_instance_and_bounded_restart() -> None:
    installer = (
        ROOT / "scripts/windows/Install-ODIN-Autonomous-Demo-RC2-Task.ps1"
    ).read_text(encoding="utf-8")
    launcher = (
        ROOT / "scripts/windows/Start-ODIN-Autonomous-Demo-RC2.ps1"
    ).read_text(encoding="utf-8")

    assert "-AtLogOn" in installer
    assert "-RunLevel Limited" in installer
    assert "-LogonType Interactive" in installer
    assert "-MultipleInstances IgnoreNew" in installer
    assert "-RestartCount 3" in installer
    assert "-ExecutionTimeLimit ([TimeSpan]::Zero)" in installer
    assert "ODIN_OANDA_PASSWORD" not in installer + launcher
    assert r"C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe" in launcher
    assert r"D:\ODIN_LOCAL\mt5\terminal64.exe" in launcher


def test_safe_stop_and_pause_controls_do_not_stop_observability() -> None:
    control = (
        ROOT / "scripts/windows/Set-ODIN-Autonomous-Demo-Control.ps1"
    ).read_text(encoding="utf-8")

    assert "PAUSE" in control
    assert "SAFE_STOP" in control
    assert "RESUME" in control
    assert "ConfirmResume" in control
    assert "Stop-ScheduledTask" not in control
    assert "execution_allowed = $false" in control
    assert "real_trading = $false" in control

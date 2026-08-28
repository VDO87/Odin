import ast
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


def test_canary_launcher_requires_explicit_one_shot_confirmation() -> None:
    launcher = (
        ROOT / "scripts/windows/Invoke-ODIN-MT5-Demo-Canary-OneShot.ps1"
    ).read_text(encoding="utf-8")
    lowered = launcher.lower()

    assert "[switch]$confirmoneshot" in lowered
    assert "confirm_one_demo_canary" in lowered
    assert r"C:\Program Files\OANDA TMS MT5 Terminal\terminal64.exe" in launcher
    assert "ODIN_OANDA_ACCOUNT_MODE" in launcher
    assert "ODIN_OANDA_LOGIN" in launcher
    assert "ODIN_OANDA_SERVER" in launcher
    assert "ODIN_OANDA_PASSWORD" not in launcher
    assert ".demo_canary_attempted.json" in launcher
    assert "order_send" not in lowered


def test_canary_probe_uses_gate_service_without_second_submission_call() -> None:
    probe = ROOT / "scripts/windows/mt5_demo_canary_one_shot.py"
    source = probe.read_text(encoding="utf-8")

    assert "run_demo_canary" in source
    assert "CanaryAuthorization" in source
    assert "account_fingerprint" in source
    assert "evaluate_demo_execution_gate" in source
    assert "mt5.initialize" in source
    assert "mt5.account_info" in source
    assert "mt5.positions_get" in source
    assert "mt5.orders_get" in source
    assert "mt5.shutdown" in source
    assert "EXPLICIT_DEMO_CANARY_ONE_SHOT" in source
    assert _attribute_calls(probe, "order_send") == []


def test_repo_control_remains_disarmed_for_canary_runner() -> None:
    control = (ROOT / "config/demo_execution_rc1.json").read_text(encoding="utf-8")
    assert '"canary_authorized": false' in control
    assert '"fixed_volume": 0.01' in control
    assert '"safe_to_trade": false' in control
    assert '"real_trading": false' in control
    assert '"execution_allowed": false' in control


def test_only_isolated_adapter_contains_submission_call() -> None:
    calls: list[tuple[Path, int]] = []
    for path in (ROOT / "src").rglob("*.py"):
        calls.extend((path, line) for line in _attribute_calls(path, "order_send"))
    for path in (ROOT / "scripts").rglob("*.py"):
        calls.extend((path, line) for line in _attribute_calls(path, "order_send"))

    assert len(calls) == 1
    assert calls[0][0] == ROOT / "src/odin/adapters/mt5/demo_execution_adapter.py"

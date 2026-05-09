from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from odin_health.checks_network import check_network


ROOT = Path(__file__).resolve().parents[2]


def run_cmd(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    return subprocess.run(
        args,
        cwd=ROOT,
        env=merged_env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_dashboard_create_app_and_routes() -> None:
    module_path = ROOT / "apps" / "dashboard_html" / "app.py"
    spec = spec_from_file_location("dashboard_html_app_local", module_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    create_app = getattr(module, "create_app")

    app = create_app()
    for method, path in [
        ("GET", "/"),
        ("GET", "/atlas"),
        ("GET", "/logs"),
        ("GET", "/api/ask?q=Qual%20%C3%A9%20o%20estado%20do%20ODIN%3F"),
        ("GET", "/api/healthcheck"),
    ]:
        response = app.handle(method, path)
        assert response.status_code < 500


def test_dashboard_smoke_test_without_bind() -> None:
    result = run_cmd([sys.executable, "-m", "apps.dashboard_html.app", "--smoke-test"])
    assert result.returncode == 0, result.stderr + result.stdout
    assert "smoke-test" in result.stdout.lower()


def test_run_odin_smoke_test_detects_python() -> None:
    env = {"PATH": "/usr/bin:/bin"}
    result = run_cmd(["./run_odin.sh", "--smoke-test"], env=env)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "smoke-test ok" in result.stdout.lower()


def test_healthcheck_sh_detects_python_and_offline_ok() -> None:
    env = {"PATH": "/usr/bin:/bin"}
    result = run_cmd(["./healthcheck.sh", "--offline-ok"], env=env)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "FINAL_STATUS=" in result.stdout


def test_install_sh_dry_run() -> None:
    result = run_cmd(["./install.sh", "--dry-run"])
    assert result.returncode == 0, result.stderr + result.stdout
    assert "dry-run" in result.stdout.lower() or "dry-run" in result.stderr.lower()


def test_cli_smoke_test() -> None:
    result = run_cmd([sys.executable, "-m", "apps.dashboard_terminal.cli", "smoke-test"])
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["smoke_test"] == "ok"
    assert payload["atlas"]["execution_permission"] == "SHADOW_ONLY"


def test_telegram_dry_run() -> None:
    result = run_cmd([sys.executable, "-m", "apps.telegram_bot.bot", "--dry-run"])
    assert result.returncode == 0, result.stderr + result.stdout
    assert "dry_run" in result.stdout


def test_network_check_is_clear_and_safe() -> None:
    payload = check_network()
    assert payload["check"] == "network"
    assert "reason" in payload
    assert payload["status"] in {"OK", "CRITICAL"}
    assert isinstance(payload["safe_to_trade"], bool)


def test_runtime_scripts_keep_real_trading_blocked() -> None:
    script_text = (ROOT / "run_odin.sh").read_text(encoding="utf-8")
    assert 'ENABLE_REAL_TRADING="false"' in script_text
    assert 'ENABLE_AUTO_EXECUTION="false"' in script_text
    assert 'MT5_ORDER_SEND_ENABLED="false"' in script_text
    assert 'XTB_REAL_ENABLED="false"' in script_text
    assert 'BROKER_ALLOW_REAL_EXECUTION="false"' in script_text

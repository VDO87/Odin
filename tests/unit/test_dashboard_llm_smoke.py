from __future__ import annotations

import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_smoke_includes_llm_routes() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "apps.dashboard_html.app", "--smoke-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "smoke-test" in result.stdout.lower()


def test_dashboard_llm_status_endpoint_exists() -> None:
    module_path = ROOT / "apps" / "dashboard_html" / "app.py"
    spec = spec_from_file_location("dashboard_html_app_local_llm", module_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    create_app = getattr(module, "create_app")
    app = create_app()
    response = app.handle("GET", "/llm/status")
    assert response.status_code == 200

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_validate_runtime_script_dry_run(tmp_path: Path) -> None:
    odin_home = tmp_path / "ODIN_RUNTIME_VALIDATION"
    result = subprocess.run(
        ["./scripts/validate_odin_runtime.sh", "--odin-home", str(odin_home), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    json_report = odin_home / "data/runtime/install_validation_report.json"
    assert json_report.exists()
    payload = json.loads(json_report.read_text(encoding="utf-8"))
    assert payload.get("dry_run") is True

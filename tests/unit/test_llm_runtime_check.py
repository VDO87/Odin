from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_llm_runtime_check_script() -> None:
    result = subprocess.run(
        ["./scripts/check_llm_runtime.sh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["installs_models_automatically"] is False
    assert payload["fallback_active"] is True

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_atlas_profile_check_script() -> None:
    result = subprocess.run(
        ["./scripts/check_atlas_profile.sh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["execution_permission"] == "SHADOW_ONLY"
    assert payload["installs_external_atlas"] is False

from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_build_release_package() -> None:
    result = subprocess.run(
        ["./scripts/build_release_package.sh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    tar_path = ROOT / "dist/odin-rc1.7-deployment-package.tar.gz"
    assert tar_path.exists()
    with tarfile.open(tar_path, "r:gz") as tar:
        names = tar.getnames()
    assert all(not name.endswith("/.env") and not name.endswith(".env") for name in names)
    assert any(name.endswith("README-INSTALL.md") for name in names)

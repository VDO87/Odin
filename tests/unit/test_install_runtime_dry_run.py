from __future__ import annotations

import subprocess
from pathlib import Path

from odin_deploy.installer import InstallOptions, install_runtime
from odin_deploy.paths import resolve_deploy_paths


ROOT = Path(__file__).resolve().parents[2]


def test_install_runtime_dry_run_default() -> None:
    result = subprocess.run(
        ["./scripts/install_odin_runtime.sh", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout


def test_install_runtime_dry_run_custom_path(tmp_path: Path) -> None:
    target = tmp_path / "ODIN_RUNTIME_DRY_RUN"
    result = subprocess.run(
        ["./scripts/install_odin_runtime.sh", "--odin-home", str(target), "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert not target.exists()


def test_install_runtime_creates_structure_in_tempdir(tmp_path: Path) -> None:
    target = tmp_path / "ODIN_RUNTIME_CREATE"
    paths = resolve_deploy_paths(str(target))
    report = install_runtime(
        paths,
        InstallOptions(
            dry_run=False,
            offline=False,
            skip_venv=True,
            skip_deps=True,
            no_systemd=True,
            with_systemd=False,
            copy_current_app=False,
        ),
    )
    assert report["status"] == "OK"
    assert (target / "config").exists()
    assert (target / "data").exists()
    assert (target / "logs").exists()

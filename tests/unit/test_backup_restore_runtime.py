from __future__ import annotations

from pathlib import Path

from odin_deploy.backup import create_runtime_backup, restore_runtime_backup
from odin_deploy.paths import resolve_deploy_paths


def test_backup_and_restore_runtime(tmp_path: Path) -> None:
    home = tmp_path / "ODIN_RUNTIME"
    paths = resolve_deploy_paths(str(home))
    paths.config_dir.mkdir(parents=True, exist_ok=True)
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.dashboard_preview_dir.mkdir(parents=True, exist_ok=True)
    (paths.config_dir / ".env").write_text("ENABLE_REAL_TRADING=false\n", encoding="utf-8")

    backup_file = create_runtime_backup(paths, include_logs=False, dry_run=False)
    assert backup_file.exists()

    result = restore_runtime_backup(paths, backup_file, dry_run=True)
    assert result["status"] == "OK"


def test_restore_fails_with_missing_backup(tmp_path: Path) -> None:
    paths = resolve_deploy_paths(str(tmp_path / "ODIN_RUNTIME"))
    result = restore_runtime_backup(paths, tmp_path / "missing.tar.gz", dry_run=False)
    assert result["status"] == "ERROR"

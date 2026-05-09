from __future__ import annotations

import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from odin_deploy.paths import DeployPaths


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def create_runtime_backup(
    paths: DeployPaths,
    *,
    include_logs: bool = False,
    include_models: bool = False,
    dry_run: bool = False,
) -> Path:
    backup_file = paths.backup_dir / f"odin_runtime_backup_{_timestamp()}.tar.gz"
    if dry_run:
        return backup_file

    paths.backup_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "odin_home": str(paths.odin_home),
        "include_logs": include_logs,
        "include_models": include_models,
    }

    with tarfile.open(backup_file, "w:gz") as tar:
        for item in [paths.config_dir, paths.data_dir, paths.dashboard_preview_dir]:
            if item.exists():
                tar.add(item, arcname=item.relative_to(paths.odin_home))
        reports = Path("docs/reports")
        if reports.exists():
            tar.add(reports, arcname=reports)
        if include_logs and paths.log_dir.exists():
            tar.add(paths.log_dir, arcname=paths.log_dir.relative_to(paths.odin_home))
        if include_models and paths.models_dir.exists():
            tar.add(paths.models_dir, arcname=paths.models_dir.relative_to(paths.odin_home))

        info_json = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
        info_path = paths.tmp_dir / "backup_manifest.json"
        paths.tmp_dir.mkdir(parents=True, exist_ok=True)
        info_path.write_bytes(info_json)
        tar.add(info_path, arcname="backup_manifest.json")
    return backup_file


def restore_runtime_backup(paths: DeployPaths, backup_file: Path, *, dry_run: bool = False) -> dict[str, object]:
    if not backup_file.exists():
        return {"status": "ERROR", "reason": "backup_not_found"}
    if dry_run:
        return {"status": "OK", "dry_run": True, "backup_file": str(backup_file)}

    config_backup = paths.config_dir.with_name(f"config.pre_restore.{_timestamp()}")
    if paths.config_dir.exists():
        config_backup.parent.mkdir(parents=True, exist_ok=True)
        config_backup.mkdir(parents=True, exist_ok=True)
        for item in paths.config_dir.iterdir():
            target = config_backup / item.name
            if item.is_file():
                target.write_bytes(item.read_bytes())

    with tarfile.open(backup_file, "r:gz") as tar:
        members = tar.getmembers()
        if not any(member.name == "backup_manifest.json" for member in members):
            return {"status": "ERROR", "reason": "invalid_backup_archive"}
        tar.extractall(path=paths.odin_home)

    return {
        "status": "OK",
        "backup_file": str(backup_file),
        "config_backup": str(config_backup),
    }

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from odin_deploy.backup import create_runtime_backup
from odin_deploy.paths import DeployPaths, resolve_deploy_paths
from odin_deploy.service_templates import write_service_templates


@dataclass(slots=True)
class InstallOptions:
    dry_run: bool = False
    offline: bool = False
    skip_venv: bool = False
    skip_deps: bool = False
    no_systemd: bool = False
    with_systemd: bool = False
    copy_current_app: bool = True


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _safe_copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "dist",
            "backups",
            "*.pyc",
            ".env",
            ".env.local",
        ),
    )


def _ensure_env_file(paths: DeployPaths, *, dry_run: bool) -> list[str]:
    notes: list[str] = []
    source = _root_dir() / ".env.example"
    target_example = paths.env_example_file
    target_env = paths.env_file

    if dry_run:
        notes.append(f"would_copy:{source}->{target_example}")
        if not target_env.exists():
            notes.append(f"would_create:{target_env}")
        return notes

    target_example.parent.mkdir(parents=True, exist_ok=True)
    if source.exists():
        target_example.write_bytes(source.read_bytes())

    if target_env.exists():
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_path = target_env.with_name(f".env.backup.{stamp}")
        backup_path.write_bytes(target_env.read_bytes())
        notes.append(f"env_backup:{backup_path}")
    else:
        template = source.read_text(encoding="utf-8") if source.exists() else ""
        target_env.write_text(template, encoding="utf-8")
        notes.append(f"env_created:{target_env}")
    return notes


def _create_runtime_layout(paths: DeployPaths, *, dry_run: bool) -> None:
    for directory in paths.required_dirs():
        if dry_run:
            continue
        directory.mkdir(parents=True, exist_ok=True)


def _create_runtime_symlinks(paths: DeployPaths, *, dry_run: bool) -> None:
    links = {
        paths.app_dir / "data": paths.data_dir,
        paths.app_dir / "logs": paths.log_dir,
    }
    for link, target in links.items():
        if dry_run:
            continue
        if link.exists() or link.is_symlink():
            if link.is_symlink():
                link.unlink()
            elif link.is_dir():
                shutil.rmtree(link)
            else:
                link.unlink()
        link.symlink_to(target, target_is_directory=True)


def _python_bin(paths: DeployPaths) -> Path:
    return paths.venv_dir / "bin" / "python"


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str], dry_run: bool) -> subprocess.CompletedProcess[str] | None:
    if dry_run:
        return None
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False)


def install_runtime(paths: DeployPaths, options: InstallOptions) -> dict[str, Any]:
    root = _root_dir()
    report: dict[str, Any] = {
        "status": "OK",
        "mode": "install",
        "dry_run": options.dry_run,
        "odin_home": str(paths.odin_home),
        "steps": [],
        "errors": [],
    }
    _create_runtime_layout(paths, dry_run=options.dry_run)
    report["steps"].append("runtime_layout_ready")

    if options.copy_current_app:
        if not options.dry_run:
            _safe_copytree(root, paths.app_dir)
        report["steps"].append("app_copied")

    env_notes = _ensure_env_file(paths, dry_run=options.dry_run)
    report["steps"].extend(env_notes)

    if not options.skip_venv:
        if options.dry_run:
            report["steps"].append("venv_would_be_created")
        else:
            subprocess.run(["python3", "-m", "venv", str(paths.venv_dir)], check=False)
            report["steps"].append("venv_created")

    deploy_env = os.environ.copy()
    deploy_env.update(paths.as_env())
    if options.offline:
        deploy_env["PIP_NO_INDEX"] = "1"

    if not options.skip_deps and not options.skip_venv:
        python_bin = _python_bin(paths)
        if python_bin.exists():
            if options.offline:
                wheels = paths.vendor_dir / "wheels"
                req = paths.app_dir / "requirements.txt"
                if req.exists() and wheels.exists():
                    _run(
                        [
                            str(python_bin),
                            "-m",
                            "pip",
                            "install",
                            "--no-index",
                            "--find-links",
                            str(wheels),
                            "-r",
                            str(req),
                        ],
                        cwd=paths.app_dir,
                        env=deploy_env,
                        dry_run=options.dry_run,
                    )
                    report["steps"].append("deps_offline_attempted")
                else:
                    report["steps"].append("deps_offline_skipped_missing_wheels_or_requirements")
            else:
                _run([str(python_bin), "-m", "pip", "install", "-e", "."], cwd=paths.app_dir, env=deploy_env, dry_run=options.dry_run)
                report["steps"].append("deps_install_attempted")

    _create_runtime_symlinks(paths, dry_run=options.dry_run)
    report["steps"].append("app_runtime_symlinks_ready")

    if options.with_systemd and not options.no_systemd:
        if not options.dry_run:
            write_service_templates(paths)
        report["steps"].append("systemd_templates_ready")

    runtime_entry = paths.app_dir / "run_odin.sh"
    if not options.dry_run and runtime_entry.exists():
        _run([str(runtime_entry), "--dashboard-preview"], cwd=paths.app_dir, env=deploy_env, dry_run=False)
        _run([str(runtime_entry), "--smoke-test"], cwd=paths.app_dir, env=deploy_env, dry_run=False)
        report["steps"].append("runtime_smoke_attempted")
    elif not options.dry_run and not runtime_entry.exists():
        report["steps"].append("runtime_smoke_skipped_missing_run_odin")
    else:
        report["steps"].append("runtime_smoke_dry_run")

    return report


def update_runtime(
    paths: DeployPaths,
    *,
    dry_run: bool,
    backup_first: bool,
    skip_deps: bool,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": "OK",
        "mode": "update",
        "dry_run": dry_run,
        "steps": [],
        "errors": [],
    }
    if backup_first:
        backup_file = create_runtime_backup(paths, include_logs=False, dry_run=dry_run)
        report["steps"].append(f"backup:{backup_file}")
    options = InstallOptions(
        dry_run=dry_run,
        offline=False,
        skip_venv=False,
        skip_deps=skip_deps,
        with_systemd=False,
        no_systemd=True,
        copy_current_app=True,
    )
    install_report = install_runtime(paths, options)
    report["steps"].extend(install_report.get("steps", []))
    return report


def uninstall_runtime(
    paths: DeployPaths,
    *,
    dry_run: bool,
    keep_data: bool,
    keep_logs: bool,
    keep_config: bool,
    remove_systemd: bool,
) -> dict[str, Any]:
    report: dict[str, Any] = {"status": "OK", "mode": "uninstall", "dry_run": dry_run, "steps": []}
    removable: list[Path] = [paths.app_dir, paths.venv_dir, paths.vendor_dir, paths.models_dir, paths.services_dir, paths.dist_dir, paths.dashboard_preview_dir, paths.tmp_dir]
    if not keep_data:
        removable.append(paths.data_dir)
    if not keep_logs:
        removable.append(paths.log_dir)
    if not keep_config:
        removable.append(paths.config_dir)

    if dry_run:
        report["steps"] = [f"would_remove:{item}" for item in removable]
        return report

    for item in removable:
        if item.exists():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
            report["steps"].append(f"removed:{item}")
    if remove_systemd:
        report["steps"].append("systemd_remove_instruction_only")
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ODIN runtime installer")
    parser.add_argument("--odin-home", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--skip-venv", action="store_true")
    parser.add_argument("--skip-deps", action="store_true")
    parser.add_argument("--no-systemd", action="store_true")
    parser.add_argument("--with-systemd", action="store_true")
    parser.add_argument("--copy-current-app", action="store_true")
    parser.add_argument("--mode", choices=["install", "update", "uninstall"], default="install")
    parser.add_argument("--backup-first", action="store_true")
    parser.add_argument("--keep-data", action="store_true")
    parser.add_argument("--keep-logs", action="store_true")
    parser.add_argument("--keep-config", action="store_true")
    parser.add_argument("--remove-systemd", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    paths = resolve_deploy_paths(args.odin_home)
    if args.mode == "install":
        report = install_runtime(
            paths,
            InstallOptions(
                dry_run=args.dry_run,
                offline=args.offline,
                skip_venv=args.skip_venv,
                skip_deps=args.skip_deps,
                no_systemd=args.no_systemd,
                with_systemd=args.with_systemd,
                copy_current_app=True if args.copy_current_app else True,
            ),
        )
    elif args.mode == "update":
        report = update_runtime(paths, dry_run=args.dry_run, backup_first=args.backup_first, skip_deps=args.skip_deps)
    else:
        report = uninstall_runtime(
            paths,
            dry_run=args.dry_run,
            keep_data=args.keep_data or True,
            keep_logs=args.keep_logs or True,
            keep_config=args.keep_config or True,
            remove_systemd=args.remove_systemd,
        )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

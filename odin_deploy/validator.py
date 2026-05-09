from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from odin_deploy.paths import DeployPaths, resolve_deploy_paths


def _run_command(command: list[str], *, cwd: Path, env: dict[str, str], dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"command": " ".join(command), "status": "DRY_RUN", "returncode": 0}
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    return {
        "command": " ".join(command),
        "status": "OK" if result.returncode == 0 else "ERROR",
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def validate_runtime_installation(paths: DeployPaths, *, dry_run: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for directory in paths.required_dirs():
        exists = directory.exists() if not dry_run else True
        checks.append({"check": f"path:{directory}", "status": "OK" if exists else "ERROR"})

    env = os.environ.copy()
    env.update(paths.as_env())
    app_root = paths.app_dir
    commands = [
        [str(app_root / "run_odin.sh"), "--runtime-smoke-test"],
        [str(app_root / "run_odin.sh"), "--run-once"],
        [str(app_root / "run_odin.sh"), "--runtime-validate"],
        [str(app_root / "run_odin.sh"), "--soak-test-mini"],
        [str(app_root / "run_odin.sh"), "--dashboard-preview"],
        [str(app_root / "run_odin.sh"), "--dashboard-qa"],
        [str(app_root / "run_odin.sh"), "--tui-smoke-test"],
        [str(app_root / "scripts/check_llm_runtime.sh")],
        [str(app_root / "scripts/check_atlas_profile.sh")],
    ]
    cmd_results = [_run_command(cmd, cwd=app_root, env=env, dry_run=dry_run) for cmd in commands]

    status = "PASS"
    if any(item["status"] == "ERROR" for item in checks):
        status = "FAIL"
    if any(item["status"] == "ERROR" for item in cmd_results):
        status = "FAIL"

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "status": status,
        "dry_run": dry_run,
        "odin_home": str(paths.odin_home),
        "path_checks": checks,
        "command_checks": cmd_results,
    }
    return report


def write_validation_reports(paths: DeployPaths, report: dict[str, Any]) -> tuple[Path, Path]:
    json_path = paths.data_dir / "runtime" / "install_validation_report.json"
    md_path = Path("docs/reports/ODIN_RC1_7_INSTALL_VALIDATION_REPORT.md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# ODIN RC1.7 Install Validation Report",
        "",
        f"- Timestamp: `{report.get('timestamp')}`",
        f"- Status: `{report.get('status')}`",
        f"- Dry-run: `{report.get('dry_run')}`",
        f"- ODIN_HOME: `{report.get('odin_home')}`",
        "",
        "## Path checks",
    ]
    for item in report.get("path_checks", []):
        lines.append(f"- {item.get('check')}: {item.get('status')}")
    lines.append("")
    lines.append("## Command checks")
    for item in report.get("command_checks", []):
        lines.append(f"- {item.get('command')}: {item.get('status')} (rc={item.get('returncode')})")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    odin_home = os.getenv("ODIN_HOME")
    dry_run = os.getenv("ODIN_DEPLOY_DRY_RUN", "false").lower() == "true"
    paths = resolve_deploy_paths(odin_home)
    report = validate_runtime_installation(paths, dry_run=dry_run)
    json_path, md_path = write_validation_reports(paths, report)
    print(json.dumps({"status": report["status"], "json": str(json_path), "markdown": str(md_path)}, indent=2))
    return 0 if report["status"] == "PASS" or dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())

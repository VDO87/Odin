"""Local Windows bootstrap for the versioned Autonomous DEMO RC2 runtime."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import runpy
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--canonical-repo-root", required=True)
    parser.add_argument("--persistent-task", action="store_true")
    arguments = parser.parse_args()

    runtime_root = Path(arguments.runtime_root).resolve()
    installed_root = Path(__file__).resolve().parents[2]
    if runtime_root != installed_root:
        raise RuntimeError("rc2_installed_runtime_root_mismatch")

    source_root = runtime_root / "src"
    windows_scripts = runtime_root / "scripts" / "windows"
    supervisor = windows_scripts / "mt5_autonomous_demo_supervisor.py"
    if not source_root.is_dir() or not supervisor.is_file():
        raise RuntimeError("rc2_installed_runtime_incomplete")

    os.environ["ODIN_RC2_CANONICAL_REPO_ROOT"] = arguments.canonical_repo_root
    os.environ["ODIN_RC2_REPO_SRC"] = str(source_root)
    os.environ["ODIN_RC2_WINDOWS_SCRIPTS"] = str(windows_scripts)
    os.environ["ODIN_RC1_REPO_SRC"] = str(source_root)
    sys.argv = [str(supervisor)]
    if arguments.persistent_task:
        sys.argv.append("--persistent-task")
    runpy.run_path(str(supervisor), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

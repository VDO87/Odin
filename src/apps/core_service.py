from __future__ import annotations

import argparse
import json

from core.runtime import CoreRuntimeController
from shared.config import OdinSettings


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the Odin CORE runtime MVP.")
    parser.add_argument(
        "--config",
        default="config/odin.local.toml",
        help="Path to the local Odin configuration file.",
    )
    args = parser.parse_args()

    settings = OdinSettings.load(args.config)
    runtime = CoreRuntimeController(settings)
    view = runtime.start()
    print(
        json.dumps(
            {
                "state_code": view.state_code.value,
                "mode_code": view.mode_code.value,
                "status_summary": view.status_summary,
                "kill_active": view.kill_active,
                "dominant_block_reason": view.dominant_block_reason,
                "liveness": view.critical_module_liveness,
            },
            indent=2,
        )
    )

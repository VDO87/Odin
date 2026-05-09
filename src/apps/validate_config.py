from __future__ import annotations

import argparse
import json

from shared.config import OdinSettings, validate_settings
from shared.enums import ExecutionProfile


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an Odin configuration file.")
    parser.add_argument(
        "--config",
        default="config/odin.local.toml",
        help="Path to the Odin configuration file.",
    )
    parser.add_argument(
        "--expect-profile",
        choices=[profile.value for profile in ExecutionProfile],
        default=None,
        help="Optional profile expected by the caller.",
    )
    args = parser.parse_args()

    settings = OdinSettings.load(args.config)
    expected_profile = (
        ExecutionProfile(args.expect_profile) if args.expect_profile is not None else None
    )
    errors = validate_settings(settings, expected_profile=expected_profile)
    if errors:
        raise ValueError("; ".join(errors))

    print(
        json.dumps(
            {
                "profile": settings.profile.name.value,
                "dashboard_surface": settings.dashboard.surface.value,
                "learn_enabled": settings.profile.learn_enabled,
                "shadow_mode_enabled": settings.profile.shadow_mode_enabled,
                "memory_enabled": settings.memory.enabled,
                "market_profile": settings.market.profile.value,
                "instrument_scope": list(settings.market.instrument_scope),
                "feed_scope": list(settings.market.feed_scope),
                "news_guard_enabled": settings.market.news_guard_enabled,
                "spread_guard_enabled": settings.market.spread_guard_enabled,
                "heavy_enrichment_enabled": settings.market.heavy_enrichment_enabled,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

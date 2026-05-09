from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any

from shared.enums import DashboardSurface, ExecutionProfile, MarketProfile


@dataclass(frozen=True, slots=True)
class CoreSettings:
    startup_timeout_ms: int
    event_queue_max_size: int
    heartbeat_timeout_ms: int
    heartbeat_grace_count: int
    allow_real_mode: bool
    recovery_required_on_unclean_shutdown: bool
    persist_on_critical_transition: bool


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    state_dir: Path
    log_dir: Path
    backup_dir: Path
    memory_dir: Path


@dataclass(frozen=True, slots=True)
class MarketSettings:
    profile: MarketProfile
    instrument_scope: tuple[str, ...]
    feed_scope: tuple[str, ...]
    news_guard_enabled: bool
    spread_guard_enabled: bool
    heavy_enrichment_enabled: bool
    max_valid_age_ms: int
    max_degraded_age_ms: int
    max_valid_latency_ms: int
    max_degraded_latency_ms: int
    max_normal_spread_bps: float
    max_degraded_spread_bps: float


@dataclass(frozen=True, slots=True)
class ExecSettings:
    mode: str
    default_ttl_ms: int
    default_max_slippage: float


@dataclass(frozen=True, slots=True)
class DecisionSettings:
    mode: str
    tactic_id: str
    test_side: str
    test_score: float
    min_score_threshold: float


@dataclass(frozen=True, slots=True)
class DashboardSettings:
    surface: DashboardSurface


@dataclass(frozen=True, slots=True)
class MemorySettings:
    enabled: bool
    provider: str
    mode: str
    freeze_into_decision_snapshot: bool
    freeze_into_learn_snapshot: bool


@dataclass(frozen=True, slots=True)
class ExternalDataSettings:
    demo_provider_enabled: bool
    alpha_vantage_enabled: bool
    trading_economics_enabled: bool
    quote_cache_ttl_seconds: int
    calendar_cache_ttl_seconds: int
    asset_search_cache_ttl_seconds: int
    alpha_vantage_rate_limit_per_minute: int
    trading_economics_rate_limit_per_minute: int


@dataclass(frozen=True, slots=True)
class ProfileSettings:
    name: ExecutionProfile
    learn_enabled: bool
    shadow_mode_enabled: bool
    auxiliary_memory_enabled: bool
    learn_queries_enabled: bool
    learn_actions_enabled: bool

    @property
    def is_lite(self) -> bool:
        return self.name == ExecutionProfile.LITE


@dataclass(frozen=True, slots=True)
class RealSettings:
    require_explicit_confirmation: bool
    confirmation_phrase: str
    require_change_ticket: bool
    require_approval_ref: bool
    require_all_heartbeats_ok: bool
    stricter_max_slippage_factor: float
    execution_adapter_name: str
    audit_export_dir: Path


@dataclass(frozen=True, slots=True)
class OdinSettings:
    profile: ProfileSettings
    core: CoreSettings
    runtime: RuntimeSettings
    market: MarketSettings
    exec: ExecSettings
    decision: DecisionSettings
    dashboard: DashboardSettings
    memory: MemorySettings
    external_data: ExternalDataSettings
    real: RealSettings

    @classmethod
    def load(cls, path: str | Path) -> "OdinSettings":
        raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_raw(raw)

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "OdinSettings":
        core_raw = raw["core"]
        runtime_raw = raw["runtime"]
        profile_raw = raw.get("profile", {})
        market_raw = raw.get("market", {})
        exec_raw = raw.get("exec", {})
        decision_raw = raw.get("decision", {})
        memory_raw = raw.get("memory", {})
        external_data_raw = raw.get("external_data", {})
        real_raw = raw.get("real", {})

        runtime_settings = RuntimeSettings(
            state_dir=Path(runtime_raw["state_dir"]),
            log_dir=Path(runtime_raw["log_dir"]),
            backup_dir=Path(runtime_raw["backup_dir"]),
            memory_dir=Path(runtime_raw.get("memory_dir", "runtime/memory")),
        )

        profile_name = ExecutionProfile(
            str(profile_raw.get("name", runtime_raw.get("execution_profile", "lite"))).lower()
        )
        profile_settings = _profile_settings(
            profile_name,
            raw_memory_enabled=bool(memory_raw.get("enabled", False)),
        )
        dashboard_surface = _dashboard_surface_for_profile(profile_name)
        market_profile = _market_profile_for_execution_profile(profile_name)

        instrument_scope = _load_instrument_scope(
            market_raw.get("instrument_scope"),
            default=("EURUSD",),
        )
        if profile_name == ExecutionProfile.LITE and instrument_scope:
            instrument_scope = instrument_scope[:1]
        feed_scope = _load_scope(
            market_raw.get("feed_scope"),
            default=("primary",),
        )
        if profile_name == ExecutionProfile.LITE and feed_scope:
            feed_scope = feed_scope[:1]

        news_guard_enabled = bool(
            market_raw.get("news_guard_enabled", profile_name != ExecutionProfile.LITE)
        )
        if profile_name == ExecutionProfile.LITE:
            news_guard_enabled = False

        spread_guard_enabled = bool(market_raw.get("spread_guard_enabled", True))
        if profile_name == ExecutionProfile.LITE:
            spread_guard_enabled = True

        heavy_enrichment_enabled = bool(
            market_raw.get("heavy_enrichment_enabled", profile_name != ExecutionProfile.LITE)
        )
        if profile_name == ExecutionProfile.LITE:
            heavy_enrichment_enabled = False

        memory_enabled = profile_settings.auxiliary_memory_enabled

        return cls(
            profile=profile_settings,
            core=CoreSettings(
                startup_timeout_ms=int(core_raw["startup_timeout_ms"]),
                event_queue_max_size=int(core_raw["event_queue_max_size"]),
                heartbeat_timeout_ms=int(core_raw["heartbeat_timeout_ms"]),
                heartbeat_grace_count=int(core_raw["heartbeat_grace_count"]),
                allow_real_mode=bool(core_raw["allow_real_mode"]),
                recovery_required_on_unclean_shutdown=bool(
                    core_raw["recovery_required_on_unclean_shutdown"]
                ),
                persist_on_critical_transition=bool(core_raw["persist_on_critical_transition"]),
            ),
            runtime=runtime_settings,
            market=MarketSettings(
                profile=market_profile,
                instrument_scope=instrument_scope,
                feed_scope=feed_scope,
                news_guard_enabled=news_guard_enabled,
                spread_guard_enabled=spread_guard_enabled,
                heavy_enrichment_enabled=heavy_enrichment_enabled,
                max_valid_age_ms=int(market_raw.get("max_valid_age_ms", 1_000)),
                max_degraded_age_ms=int(market_raw.get("max_degraded_age_ms", 3_000)),
                max_valid_latency_ms=int(market_raw.get("max_valid_latency_ms", 250)),
                max_degraded_latency_ms=int(market_raw.get("max_degraded_latency_ms", 1_000)),
                max_normal_spread_bps=float(market_raw.get("max_normal_spread_bps", 2.5)),
                max_degraded_spread_bps=float(market_raw.get("max_degraded_spread_bps", 6.0)),
            ),
            exec=ExecSettings(
                mode=str(exec_raw.get("mode", "demo")),
                default_ttl_ms=int(exec_raw.get("default_ttl_ms", 3_000)),
                default_max_slippage=float(exec_raw.get("default_max_slippage", 0.0002)),
            ),
            decision=DecisionSettings(
                mode=str(decision_raw.get("mode", "safe")).lower(),
                tactic_id=str(
                    decision_raw.get(
                        "tactic_id",
                        "demo_liquidity_or_simple_momentum_v1",
                    )
                ),
                test_side=str(decision_raw.get("test_side", "BUY")).upper(),
                test_score=float(decision_raw.get("test_score", 0.91)),
                min_score_threshold=float(decision_raw.get("min_score_threshold", 0.8)),
            ),
            dashboard=DashboardSettings(surface=dashboard_surface),
            memory=MemorySettings(
                enabled=memory_enabled,
                provider=str(memory_raw.get("provider", "mempalace")),
                mode=str(memory_raw.get("mode", "advisory")),
                freeze_into_decision_snapshot=memory_enabled
                and bool(memory_raw.get("freeze_into_decision_snapshot", True)),
                freeze_into_learn_snapshot=memory_enabled
                and profile_settings.learn_enabled
                and bool(memory_raw.get("freeze_into_learn_snapshot", True)),
            ),
            external_data=ExternalDataSettings(
                demo_provider_enabled=bool(external_data_raw.get("demo_provider_enabled", True)),
                alpha_vantage_enabled=(
                    profile_name in {ExecutionProfile.STANDARD, ExecutionProfile.FULL}
                    and bool(external_data_raw.get("alpha_vantage_enabled", False))
                ),
                trading_economics_enabled=(
                    profile_name in {ExecutionProfile.STANDARD, ExecutionProfile.FULL}
                    and bool(external_data_raw.get("trading_economics_enabled", False))
                ),
                quote_cache_ttl_seconds=int(external_data_raw.get("quote_cache_ttl_seconds", 30)),
                calendar_cache_ttl_seconds=int(
                    external_data_raw.get("calendar_cache_ttl_seconds", 300)
                ),
                asset_search_cache_ttl_seconds=int(
                    external_data_raw.get("asset_search_cache_ttl_seconds", 300)
                ),
                alpha_vantage_rate_limit_per_minute=int(
                    external_data_raw.get("alpha_vantage_rate_limit_per_minute", 5)
                ),
                trading_economics_rate_limit_per_minute=int(
                    external_data_raw.get("trading_economics_rate_limit_per_minute", 30)
                ),
            ),
            real=RealSettings(
                require_explicit_confirmation=bool(
                    real_raw.get("require_explicit_confirmation", True)
                ),
                confirmation_phrase=str(
                    real_raw.get("confirmation_phrase", "CONFIRM_REAL_MODE")
                ),
                require_change_ticket=bool(real_raw.get("require_change_ticket", True)),
                require_approval_ref=bool(real_raw.get("require_approval_ref", True)),
                require_all_heartbeats_ok=bool(real_raw.get("require_all_heartbeats_ok", True)),
                stricter_max_slippage_factor=float(
                    real_raw.get("stricter_max_slippage_factor", 0.5)
                ),
                execution_adapter_name=str(
                    real_raw.get("execution_adapter_name", "simulated_real")
                ),
                audit_export_dir=Path(
                    real_raw.get(
                        "audit_export_dir",
                        str(runtime_settings.log_dir / "real-audit"),
                    )
                ),
            ),
        )


def validate_settings(
    settings: OdinSettings,
    *,
    expected_profile: ExecutionProfile | None = None,
) -> list[str]:
    errors: list[str] = []
    if expected_profile is not None and settings.profile.name != expected_profile:
        errors.append(
            f"expected profile {expected_profile.value} but config resolved to {settings.profile.name.value}"
        )

    if settings.profile.is_lite:
        if settings.profile.learn_enabled:
            errors.append("lite profile must keep learn disabled")
        if settings.profile.shadow_mode_enabled:
            errors.append("lite profile must keep shadow mode disabled")
        if settings.memory.enabled:
            errors.append("lite profile must keep auxiliary memory disabled")
        if settings.dashboard.surface.value != "lite":
            errors.append("lite profile must expose dash-lite")
        if len(settings.market.instrument_scope) > 1:
            errors.append("lite profile must keep market instrument scope to one instrument")
        if len(settings.market.feed_scope) > 1:
            errors.append("lite profile must keep market feed scope to one feed")
        if settings.market.news_guard_enabled:
            errors.append("lite profile must keep market news guard disabled by default")
        if settings.market.heavy_enrichment_enabled:
            errors.append("lite profile must keep heavy market enrichment disabled")
        if settings.external_data.alpha_vantage_enabled:
            errors.append("lite profile must keep alpha_vantage disabled")
        if settings.external_data.trading_economics_enabled:
            errors.append("lite profile must keep trading_economics disabled")
    if not settings.external_data.demo_provider_enabled:
        errors.append("external_data must keep demo_provider_enabled=true")
    if settings.decision.mode not in {"safe", "test"}:
        errors.append("decision.mode must be 'safe' or 'test'")
    if settings.decision.test_side not in {"BUY", "SELL"}:
        errors.append("decision.test_side must be BUY or SELL")
    return errors


def _profile_settings(
    profile_name: ExecutionProfile,
    *,
    raw_memory_enabled: bool,
) -> ProfileSettings:
    if profile_name == ExecutionProfile.FULL:
        return ProfileSettings(
            name=profile_name,
            learn_enabled=True,
            shadow_mode_enabled=True,
            auxiliary_memory_enabled=raw_memory_enabled,
            learn_queries_enabled=True,
            learn_actions_enabled=True,
        )
    return ProfileSettings(
        name=profile_name,
        learn_enabled=False,
        shadow_mode_enabled=False,
        auxiliary_memory_enabled=False,
        learn_queries_enabled=False,
        learn_actions_enabled=False,
    )


def _dashboard_surface_for_profile(profile_name: ExecutionProfile) -> DashboardSurface:
    if profile_name == ExecutionProfile.LITE:
        return DashboardSurface.LITE
    if profile_name == ExecutionProfile.STANDARD:
        return DashboardSurface.STANDARD
    return DashboardSurface.FULL


def _market_profile_for_execution_profile(profile_name: ExecutionProfile) -> MarketProfile:
    if profile_name == ExecutionProfile.LITE:
        return MarketProfile.SIMPLE
    if profile_name == ExecutionProfile.STANDARD:
        return MarketProfile.STANDARD
    return MarketProfile.FULL


def _load_instrument_scope(value: object, *, default: tuple[str, ...]) -> tuple[str, ...]:
    return _load_scope(value, default=default)


def _load_scope(value: object, *, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip()
        return (normalized,) if normalized else default
    if isinstance(value, list):
        normalized_values = tuple(str(item).strip() for item in value if str(item).strip())
        return normalized_values or default
    return default

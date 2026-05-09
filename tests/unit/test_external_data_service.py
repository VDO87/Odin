from __future__ import annotations

from pathlib import Path

from external_data import ExternalDataAuditLog, ExternalDataService
from shared.config import OdinSettings


def _build_settings(tmp_path: Path, *, profile: str, extra_external_data: str = "") -> OdinSettings:
    config_path = tmp_path / "odin.external.toml"
    config_path.write_text(
        f"""
[profile]
name = "{profile}"

[core]
startup_timeout_ms = 15000
event_queue_max_size = 2048
heartbeat_timeout_ms = 500
heartbeat_grace_count = 1
allow_real_mode = false
recovery_required_on_unclean_shutdown = true
persist_on_critical_transition = true

[memory]
enabled = false
provider = "mempalace"
mode = "advisory"
freeze_into_decision_snapshot = true
freeze_into_learn_snapshot = true

[runtime]
state_dir = "{tmp_path / 'state'}"
log_dir = "{tmp_path / 'logs'}"
backup_dir = "{tmp_path / 'backups'}"
memory_dir = "{tmp_path / 'memory'}"

[external_data]
{extra_external_data}
""",
        encoding="utf-8",
    )
    return OdinSettings.load(config_path)


def test_external_data_service_lite_profile_uses_demo_without_real_dependencies(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path, profile="lite")
    service = ExternalDataService(
        settings,
        audit_log=ExternalDataAuditLog(settings.runtime.log_dir / "external-data-audit.jsonl"),
    )

    status = service.get_status_payload()
    quote_payload = service.get_quote_payload("EURUSD")
    calendar_payload = service.get_calendar_payload()

    assert status["profile"] == "lite"
    assert status["core_authority"] is False
    assert "real_provider_disabled_by_profile_or_config" in status["warnings"]
    assert quote_payload["quote"]["symbol"] == "EURUSD"
    assert quote_payload["quote"]["provider"] == "DemoProvider"
    assert calendar_payload["next_event"] is not None


def test_external_data_service_falls_back_to_demo_when_real_provider_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "dummy-key")
    settings = _build_settings(
        tmp_path,
        profile="standard",
        extra_external_data="alpha_vantage_enabled = true\ntrading_economics_enabled = false",
    )
    service = ExternalDataService(
        settings,
        audit_log=ExternalDataAuditLog(settings.runtime.log_dir / "external-data-audit.jsonl"),
    )

    quote_payload = service.get_quote_payload("EURUSD")
    status = service.get_status_payload()

    assert quote_payload["quote"]["provider"] == "DemoProvider"
    assert any(provider["provider"] == "AlphaVantage" for provider in status["providers"])


def test_external_data_service_asset_search_returns_demo_assets(tmp_path: Path) -> None:
    settings = _build_settings(tmp_path, profile="lite")
    service = ExternalDataService(
        settings,
        audit_log=ExternalDataAuditLog(settings.runtime.log_dir / "external-data-audit.jsonl"),
    )

    payload = service.search_assets_payload("ETF")

    assert payload["query"] == "ETF"
    assert any(asset["asset_class"] == "ETF" for asset in payload["assets"])


def test_external_data_missing_real_api_keys_is_warning_not_fatal(tmp_path: Path) -> None:
    settings = _build_settings(
        tmp_path,
        profile="standard",
        extra_external_data="alpha_vantage_enabled = true\ntrading_economics_enabled = true",
    )
    service = ExternalDataService(
        settings,
        audit_log=ExternalDataAuditLog(settings.runtime.log_dir / "external-data-audit.jsonl"),
    )

    status = service.get_status_payload()
    quote_payload = service.get_quote_payload("EURUSD")
    calendar_payload = service.get_calendar_payload()

    assert "real_provider_enabled_but_not_configured" in status["warnings"]
    assert quote_payload["quote"]["provider"] == "DemoProvider"
    assert calendar_payload["next_event"] is not None

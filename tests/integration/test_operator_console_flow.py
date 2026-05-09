import json
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

from core.runtime import CoreRuntimeController
from external_data.models import ExternalQuote
from market import MarketOperationalInput
from operator_console import CommandGateway, TraderConsoleService
from shared.config import OdinSettings
from shared.utils import utc_now


def write_config(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "odin.local.toml"
    config_path.write_text(
        """
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
state_dir = "__STATE_DIR__"
log_dir = "__LOG_DIR__"
backup_dir = "__BACKUP_DIR__"
memory_dir = "__MEMORY_DIR__"
""".replace("__STATE_DIR__", str(tmp_path / "state"))
        .replace("__LOG_DIR__", str(tmp_path / "logs"))
        .replace("__BACKUP_DIR__", str(tmp_path / "backups"))
        .replace("__MEMORY_DIR__", str(tmp_path / "memory")),
        encoding="utf-8",
    )
    return config_path


def make_service(
    tmp_path: Path,
    *,
    status_file_path: Path | None = None,
    start_runtime: bool = True,
) -> TraderConsoleService:
    config_path = write_config(tmp_path)
    settings = OdinSettings.load(config_path)
    runtime = CoreRuntimeController(settings)
    if start_runtime:
        runtime.start()
    else:
        runtime.get_state_store().initialize()
    gateway = CommandGateway(runtime, config_path=config_path)
    return TraderConsoleService(
        runtime,
        gateway,
        config_path=config_path,
        status_file_path=status_file_path,
    )


def _dashboard_block(html: str) -> str:
    start = html.index('id="page-dashboard"')
    end = html.index('id="page-market"')
    return html[start:end]


def _seed_stale_quote_cache(service: TraderConsoleService, *, age_seconds: int = 20) -> None:
    stale_quote = ExternalQuote(
        symbol="EURUSD",
        provider="DemoProvider",
        timestamp_utc=utc_now() - timedelta(seconds=age_seconds),
        bid=1.0818,
        ask=1.0820,
        last_price=1.0819,
        currency="USD",
        from_cache=False,
        warning=None,
    )
    service.external_data_service._cache.set(  # noqa: SLF001 - integration test setup
        "quote:EURUSD",
        stale_quote,
        ttl_seconds=30,
    )


def test_status_endpoint_with_valid_core_public_view_file(tmp_path: Path) -> None:
    status_file = tmp_path / "state" / "core_public_view.json"
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(
        json.dumps({"event": "core_state_update", "state_code": "ST-10"}),
        encoding="utf-8",
    )
    service = make_service(tmp_path, status_file_path=status_file)

    payload = service.get_status_payload()

    assert payload["status_source"] == "core_public_view_file"
    assert payload["status_file_present"] is True
    assert payload["status_file_payload"]["event"] == "core_state_update"
    assert payload["global_state"] == "ST-10"
    assert payload["mode"] is not None
    assert payload["readiness"] is not None
    assert payload["integrity"] is not None
    assert isinstance(payload["liveness"], dict)


def test_status_endpoint_without_status_file(tmp_path: Path) -> None:
    service = make_service(tmp_path, status_file_path=tmp_path / "state" / "missing.json")

    payload = service.get_status_payload()

    assert payload["status_source"] == "runtime_memory"
    assert payload["status_file_present"] is False
    assert payload["status_file_payload"] is None
    assert payload["global_state"].startswith("ST-")


def test_external_data_payloads_are_available_in_console_service(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    status_payload = service.get_external_status_payload()
    quote_payload = service.get_external_quote_payload("EURUSD")
    calendar_payload = service.get_external_calendar_payload()
    search_payload = service.get_external_asset_search_payload("ETF")

    assert status_payload["core_authority"] is False
    assert status_payload["data_can_execute_orders"] is False
    assert any(provider["provider"] == "DemoProvider" for provider in status_payload["providers"])
    assert quote_payload["quote"]["symbol"] == "EURUSD"
    assert quote_payload["quote"]["provider"] == "DemoProvider"
    assert calendar_payload["events"]
    assert search_payload["assets"]


def test_hash_routes_and_pages_are_declared_and_hidden_by_default(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    html = service.get_index_html()
    js = service.get_static_asset("app.js")[0].decode("utf-8")

    for route in (
        "dashboard",
        "market",
        "risk",
        "decision",
        "execution",
        "portfolios",
        "market-data",
        "economic-calendar",
        "logs",
        "config",
        "commands",
        "integrations",
        "intelligence",
    ):
        assert f'data-route="{route}"' in html
        assert f'id="page-{route}"' in html
    assert 'id="page-dashboard" class="route-page"' in html
    assert 'id="page-market" class="route-page hidden"' in html
    assert 'id="page-config" class="route-page hidden"' in html
    assert "function setActiveRoute(route)" in js
    assert 'window.addEventListener("hashchange", applyRouteFromHash);' in js
    assert "section.classList.add(\"hidden\")" in js


def test_dashboard_does_not_contain_full_config_or_future_pages(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    html = service.get_index_html()
    dashboard = _dashboard_block(html)

    assert "Estado Crítico" in dashboard
    assert "Diagnóstico Automático" in dashboard
    assert "Controlos Operacionais Principais" in dashboard
    assert "Integrações" not in dashboard
    assert "Intelligence" not in dashboard
    assert "Configuração Atual" not in dashboard
    assert "Staged Config" not in dashboard


def test_sidebar_groups_do_not_duplicate_dashboard_in_administration(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    html = service.get_index_html()
    admin_start = html.index("<span class=\"menu-title\">ADMINISTRAÇÃO</span>")
    admin_end = html.index("<span class=\"menu-title\">DADOS</span>")
    admin_block = html[admin_start:admin_end]

    assert ">Dashboard<" not in admin_block
    assert ">Config<" in admin_block
    assert ">Commands<" in admin_block
    assert "<span class=\"menu-title\">DADOS</span>" in html
    assert ">Market Data<" in html
    assert ">Economic Calendar<" in html


def test_menu_active_changes_with_hash_router_logic(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    js = service.get_static_asset("app.js")[0].decode("utf-8")

    assert "link.classList.toggle(\"active\", link.dataset.route === route);" in js
    assert "applyRouteFromHash();" in js
    assert "normalizeRoute(window.location.hash)" in js


def test_frontend_refresh_uses_real_runtime_endpoints_without_mock_fallback(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    js = service.get_static_asset("app.js")[0].decode("utf-8")

    assert 'fetchJson("/api/status")' in js
    assert 'fetchJson("/api/health")' in js
    assert 'fetchJson("/api/logs/recent")' in js
    assert 'fetchJson("/api/config")' in js
    assert "__ODIN_MOCK" not in js


def test_mode_operator_hides_raw_json_and_mode_technical_has_payloads(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    html = service.get_index_html()
    js = service.get_static_asset("app.js")[0].decode("utf-8")

    assert "id=\"techDashboard\"" in html
    assert "id=\"techMarket\"" in html
    assert "id=\"techRisk\"" in html
    assert "id=\"techExecution\"" in html
    assert "class=\"panel page-tech hidden\"" in html
    assert "function renderTechnicalForRoute(" in js
    assert "function renderDashboard(" in js
    assert "function renderMarket(" in js
    assert "function renderRisk(" in js
    assert "function renderDecision(" in js
    assert "function renderExecution(" in js
    assert "function renderPortfolios(" in js
    assert "function renderMarketData(" in js
    assert "function renderEconomicCalendar(" in js
    assert "function renderLogs(" in js
    assert "function renderConfig(" in js
    assert "function renderCommands(" in js
    assert "function renderIntegrations(" in js
    assert "function renderIntelligence(" in js
    assert "setMode(uiMode.OPERATOR);" in js
    assert "setMode(uiMode.TECHNICAL)" in js


def test_external_inject_demo_quote_to_market_updates_runtime_status(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    baseline = service.get_status_payload()["market_runtime"]
    result = service.post_external_inject_demo_quote_to_market_payload(
        {
            "requested_by": "operator-1",
            "role": "operator",
            "authorization_context": {"ticket": "ops-1"},
        }
    )
    updated = service.get_status_payload()["market_runtime"]

    assert baseline["last_gate_status"] == "idle"
    assert result["gate_status"] == "accepted"
    assert result["accepted"] is True
    assert result["reason_code"] is None
    assert result["instrument_id"] == "EURUSD"
    assert result["feed_id"] == "primary"
    assert result["runtime"]["last_instrument_id"] == "EURUSD"
    assert result["runtime"]["last_feed_id"] == "primary"
    assert result["sample_age_ms"] >= 0
    assert result["max_valid_age_ms"] > 0
    assert result["market_assessment_state"] is not None
    assert isinstance(result["decision_market_ready"], bool)
    assert updated["last_gate_status"] == "accepted"
    assert updated["last_instrument_id"] == "EURUSD"


def test_external_inject_refreshes_stale_cached_quote_before_market_ingest(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    _seed_stale_quote_cache(service, age_seconds=25)

    result = service.post_external_inject_demo_quote_to_market_payload(
        {"requested_by": "operator-1", "role": "operator"}
    )

    assert result["accepted"] is True
    assert result["quote"]["provider"] == "DemoProvider"
    assert result["quote_refreshed_before_ingest"] is True
    assert result["decision_market_ready"] is True
    assert result["sample_age_ms"] <= result["max_degraded_age_ms"]
    assert result["market_assessment_reason_code"] in {"market_ready", "market_degraded", "news_guard_active"}


def test_health_endpoint_exposes_liveness_and_startup_fields(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    payload = service.get_health_payload()

    assert isinstance(payload["liveness"], dict)
    assert "startup_required_modules" in payload
    assert "startup_missing_heartbeat_modules" in payload
    assert "startup_unavailable_modules" in payload
    assert "critical_module_ok_count" in payload
    assert "critical_module_delayed_count" in payload
    assert "critical_module_timeout_count" in payload


def test_all_dom_ids_referenced_by_app_js_exist_in_html(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    html = service.get_index_html()
    js = service.get_static_asset("app.js")[0].decode("utf-8")

    html_ids = set()
    for fragment in html.split('id="')[1:]:
        html_ids.add(fragment.split('"', 1)[0])

    referenced_ids = set()
    for fragment in js.split('byId("')[1:]:
        referenced_ids.add(fragment.split('"', 1)[0])
    for fragment in js.split('document.getElementById("')[1:]:
        referenced_ids.add(fragment.split('"', 1)[0])

    missing_ids = sorted(referenced_ids - html_ids)
    assert missing_ids == []


def test_critical_commands_rejected_when_runtime_not_active(tmp_path: Path) -> None:
    service = make_service(tmp_path, start_runtime=False)
    pause_result = service.post_command_payload(
        "pause",
        {
            "requested_by": "operator-1",
            "role": "operator",
            "confirmation": True,
            "authorization_context": {"ticket": "ops-1"},
        },
    )

    assert pause_result["accepted"] is False
    assert pause_result["rejection_reason"] == "runtime_not_active"
    assert pause_result["reason_code"] == "runtime_not_active"


def test_server_js_declares_required_operator_console_endpoints(tmp_path: Path) -> None:
    server_source = Path("src/operator_console/server.py").read_text(encoding="utf-8")

    required_get = (
        "/api/status",
        "/api/health",
        "/api/config",
        "/api/external/status",
        "/api/external/quote",
        "/api/external/calendar",
    )
    required_post = (
        "/api/external/inject-demo-quote-to-market",
        "/api/test/run-decision-cycle",
        "/api/intelligence/ask",
        "/api/commands/pause",
        "/api/commands/resume",
        "/api/commands/stop",
        "/api/logs/export",
    )
    for endpoint in required_get + required_post:
        assert endpoint in server_source


def test_pause_resume_stop_and_export_logs_go_through_gateway(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    pause_result = service.post_command_payload(
        "pause",
        {
            "requested_by": "operator-1",
            "role": "operator",
            "confirmation": True,
            "authorization_context": {"ticket": "ops-1"},
        },
    )
    resume_result = service.post_command_payload(
        "resume",
        {
            "requested_by": "operator-1",
            "role": "operator",
            "confirmation": True,
            "authorization_context": {"ticket": "ops-2"},
        },
    )
    stop_result = service.post_command_payload(
        "stop",
        {
            "requested_by": "operator-1",
            "role": "operator",
            "confirmation": True,
            "authorization_context": {"ticket": "ops-3"},
        },
    )
    export_result = service.post_export_logs_payload(
        {
            "requested_by": "operator-1",
            "role": "operator",
            "authorization_context": {"ticket": "ops-4"},
            "payload": {"export_path": str(tmp_path / "logs" / "export.json")},
        }
    )

    assert pause_result["command"] == "pause"
    assert resume_result["command"] == "resume"
    assert stop_result["command"] == "stop"
    assert export_result["command"] == "export-logs"
    audit_path = tmp_path / "logs" / "operator-console-audit.jsonl"
    assert audit_path.exists() is True
    audit_text = audit_path.read_text(encoding="utf-8")
    assert "\"command\": \"pause\"" in audit_text
    assert "\"command\": \"resume\"" in audit_text
    assert "\"command\": \"stop\"" in audit_text
    assert "\"command\": \"export-logs\"" in audit_text


def test_critical_commands_require_confirmation_when_missing(tmp_path: Path) -> None:
    service = make_service(tmp_path)

    for command in ("pause", "resume", "stop"):
        result = service.post_command_payload(
            command,
            {
                "requested_by": "operator-1",
                "role": "operator",
                "confirmation": False,
                "authorization_context": {"ticket": f"ops-{command}-missing-confirm"},
            },
        )
        assert result["command"] == command
        assert result["accepted"] is False
        assert result["rejection_reason"] == "confirmation_required"
        assert result["reason_code"] == "confirmation_required"
        assert result["confirmation_required"] is True


def test_pause_command_accepts_with_confirmation(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    result = service.post_command_payload(
        "pause",
        {
            "requested_by": "operator-1",
            "role": "operator",
            "confirmation": True,
            "authorization_context": {"ticket": "ops-pause-confirm-1"},
        },
    )

    assert result["command"] == "pause"
    assert result["accepted"] is True
    assert result["rejection_reason"] is None
    assert result["reason_code"] is None
    assert result["confirmation_required"] is False


def test_read_only_queries_do_not_pollute_operational_recent_events(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    _ = service.get_status_payload()
    _ = service.get_health_payload()
    _ = service.get_config_payload()
    _ = service.get_external_status_payload()
    recent = service.get_recent_logs_payload()

    assert recent["recent_events"] == []
    assert recent["operator_recent_events"] == []
    technical_commands = [event.get("command") for event in recent["technical_recent_events"]]
    assert "status" in technical_commands
    assert "health" in technical_commands
    assert "get-config" in technical_commands
    assert "external/status" in technical_commands
    assert all(
        event.get("event_type") == "read_query" for event in recent["technical_recent_events"]
    )


def test_operational_recent_events_include_inject_and_rejected_commands(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    _ = service.post_external_inject_demo_quote_to_market_payload(
        {
            "requested_by": "operator-1",
            "role": "operator",
            "authorization_context": {"ticket": "ops-1"},
        }
    )
    _ = service.post_command_payload(
        "pause",
        {
            "requested_by": "operator-1",
            "role": "operator",
            "confirmation": False,
            "authorization_context": {"ticket": "ops-2"},
        },
    )

    recent = service.get_recent_logs_payload()["operator_recent_events"]
    commands = [event.get("command") for event in recent]
    assert "inject-demo-quote-to-market" in commands
    assert "pause" in commands
    pause_events = [event for event in recent if event.get("command") == "pause"]
    assert any(event.get("accepted") is False for event in pause_events)
    assert any(event.get("rejection_reason") == "confirmation_required" for event in pause_events)


def test_decision_cycle_test_mode_emits_demo_intent_and_updates_ledger(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    _seed_stale_quote_cache(service, age_seconds=25)
    _ = service.post_external_inject_demo_quote_to_market_payload(
        {"requested_by": "operator-1", "role": "operator"}
    )

    result = service.post_run_decision_cycle_payload(
        {"requested_by": "operator-1", "role": "operator", "mode": "test"}
    )
    status = service.get_status_payload()

    assert result["accepted"] is True
    assert result["decision"]["operational_output"] == "CANDIDATE_SELECTED"
    assert result["decision"]["intent_emitted"] is True
    assert result["intent"] is not None
    assert result["decision_summary"]["decision_cycle_id"] == result["decision"]["decision_cycle_id"]
    assert result["decision_summary"]["operational_output"] == "CANDIDATE_SELECTED"
    assert result["decision_summary"]["reason_summary"] == result["decision"]["reason_summary"]
    assert result["decision_summary"]["tactic_id"] == "demo_liquidity_or_simple_momentum_v1"
    assert result["decision_summary"]["score"] is not None
    assert result["decision_summary"]["intent_id"] == result["intent"]["intent_id"]
    assert result["decision_summary"]["execution_ledger_ref"] is not None
    assert result["market_debug"]["decision_market_ready"] is True
    assert status["decision_last_result"]["operational_output"] == "CANDIDATE_SELECTED"
    assert status["decision_last_result"]["executed_in_demo"] is True
    latest_execution = status["execution_summary"]["last_execution"]
    assert latest_execution is not None
    assert latest_execution["intent_id"] == result["intent"]["intent_id"]
    assert latest_execution["decision_cycle_id"] == result["decision"]["decision_cycle_id"]


def test_decision_cycle_safe_mode_defaults_to_no_action(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    _seed_stale_quote_cache(service, age_seconds=25)
    _ = service.post_external_inject_demo_quote_to_market_payload(
        {"requested_by": "operator-1", "role": "operator"}
    )

    result = service.post_run_decision_cycle_payload(
        {"requested_by": "operator-1", "role": "operator"}
    )
    status = service.get_status_payload()

    assert result["accepted"] is False
    assert result["decision_mode"] == "safe"
    assert result["decision"]["operational_output"] == "NO_ACTION"
    assert result["decision_summary"]["operational_output"] == "NO_ACTION"
    assert result["decision_summary"]["execution_ledger_ref"] is None
    assert result["market_debug"]["decision_market_ready"] is True
    assert result["intent"] is None
    assert status["decision_last_result"]["operational_output"] == "NO_ACTION"


def test_decision_cycle_blocks_market_when_last_sample_is_stale(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    now = utc_now()
    observed_at = now - timedelta(seconds=20)
    service.runtime.ingest_market_sample(
        MarketOperationalInput(
            instrument_id="EURUSD",
            feed_id="primary",
            feed_available=True,
            market_open=True,
            sample_valid=True,
            sample_age_ms=20_000,
            latency_ms=50,
            spread_bps=1.0,
            observed_at_utc=observed_at,
            last_valid_update_utc=observed_at,
        )
    )

    result = service.post_run_decision_cycle_payload(
        {"requested_by": "operator-1", "role": "operator", "mode": "test"}
    )

    assert result["accepted"] is False
    assert result["decision"]["operational_output"] == "BLOCKED_BY_MARKET"
    assert result["market_debug"]["decision_market_ready"] is False
    assert result["market_debug"]["reason_code"] == "feed_too_stale"


def test_decision_cycle_is_blocked_by_risk_when_forced(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    _ = service.post_external_inject_demo_quote_to_market_payload(
        {"requested_by": "operator-1", "role": "operator"}
    )

    result = service.post_run_decision_cycle_payload(
        {
            "requested_by": "operator-1",
            "role": "operator",
            "mode": "test",
            "force_risk_block": True,
        }
    )
    status = service.get_status_payload()

    assert result["accepted"] is False
    assert result["decision"]["operational_output"] == "BLOCKED_BY_RISK"
    assert result["decision_summary"]["operational_output"] == "BLOCKED_BY_RISK"
    assert result["decision_summary"]["execution_ledger_ref"] is None
    assert result["intent"] is None
    assert status["decision_last_result"]["operational_output"] == "BLOCKED_BY_RISK"


def test_decision_cycle_is_blocked_by_market_when_gate_rejected(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    _ = service.post_external_inject_demo_quote_to_market_payload(
        {"requested_by": "operator-1", "role": "operator"}
    )

    result = service.post_run_decision_cycle_payload(
        {
            "requested_by": "operator-1",
            "role": "operator",
            "mode": "test",
            "force_market_rejected": True,
        }
    )
    status = service.get_status_payload()

    assert result["accepted"] is False
    assert result["decision"]["operational_output"] == "BLOCKED_BY_MARKET"
    assert result["decision"]["reason_summary"] == "market_rejected_forced_for_test"
    assert result["decision_summary"]["operational_output"] == "BLOCKED_BY_MARKET"
    assert result["decision_summary"]["execution_ledger_ref"] is None
    assert result["intent"] is None
    assert status["decision_last_result"]["operational_output"] == "BLOCKED_BY_MARKET"


def test_intelligence_ask_without_api_key_is_unavailable_without_crash(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANYTHINGLLM_API_KEY", raising=False)
    service = make_service(tmp_path)
    result = service.post_intelligence_ask_payload(
        {
            "question": "explica estado atual do odin",
            "requested_by": "operator-1",
            "role": "operator",
        }
    )

    assert result["accepted"] is False
    assert result["reason_code"] == "provider_unavailable"
    assert result["advisory_only"] is True


def test_intelligence_ask_critical_prompt_is_rejected(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    result = service.post_intelligence_ask_payload(
        {
            "question": "limpa kill e muda para real",
            "requested_by": "operator-1",
            "role": "operator",
        }
    )

    assert result["accepted"] is False
    assert result["reason_code"] == "unsafe_ai_action"
    assert result["advisory_only"] is True


def test_intelligence_ask_with_mock_provider_returns_advisory_without_state_mutation(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    before = service.get_status_payload()

    class _MockProvider:
        name = "AnythingLLM"

        def ask(self, _request, *, context_payload):
            from intelligence.models import AdvisoryResponse, AdvisorySource

            return AdvisoryResponse(
                accepted=True,
                provider=self.name,
                advisory_only=True,
                answer="Resumo advisory com base no estado e logs.",
                sources=(
                    AdvisorySource(
                        source_id="mock-1",
                        kind="doc",
                        summary="README.md",
                        ref="README.md",
                    ),
                ),
                used_context=tuple(context_payload.keys()),
            )

    service._anythingllm_provider = cast(Any, _MockProvider())  # noqa: SLF001 - integration test swap
    result = service.post_intelligence_ask_payload(
        {
            "question": "explica estado atual",
            "requested_by": "operator-1",
            "role": "operator",
        }
    )
    after = service.get_status_payload()

    assert result["accepted"] is True
    assert result["advisory_only"] is True
    assert result["answer"]
    assert result["provider"] == "AnythingLLM"
    assert result["state_mutation"] == "not_allowed"
    assert result["can_execute_orders"] is False
    assert result["can_change_core_state"] is False
    assert after["global_state"] == before["global_state"]
    assert after["active_block_count"] == before["active_block_count"]


def test_intelligence_ask_is_auditable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANYTHINGLLM_API_KEY", raising=False)
    service = make_service(tmp_path)
    _ = service.post_intelligence_ask_payload(
        {
            "question": "explica última decisão",
            "requested_by": "operator-1",
            "role": "operator",
        }
    )

    audit_path = tmp_path / "logs" / "intelligence-advisory-audit.jsonl"
    assert audit_path.exists() is True
    audit_records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(record.get("event") == "intelligence_advisory" for record in audit_records)
    assert any(record.get("question") == "explica última decisão" for record in audit_records)
    operator_audit_path = tmp_path / "logs" / "operator-console-audit.jsonl"
    assert operator_audit_path.exists() is True
    operator_audit_text = operator_audit_path.read_text(encoding="utf-8")
    assert "\"command\": \"intelligence/ask\"" in operator_audit_text


def test_health_chart_distribution_and_recent_events_filter() -> None:
    distribution = TraderConsoleService.calculate_liveness_distribution(
        {
            "MARKET": "OK",
            "RISK": "DELAYED",
            "EXEC": "UNAVAILABLE",
            "DECISION": "NOT_STARTED",
            "RECOVERY": "TIMEOUT",
        }
    )
    assert distribution == {"ok": 1, "degraded": 2, "unavailable": 2, "nodata": 0}

    events = [
        {
            "command": "status",
            "accepted": True,
            "rejection_reason": None,
            "event_type": "read_query",
        },
        {
            "command": "external/status",
            "accepted": True,
            "rejection_reason": None,
            "event_type": "read_query",
        },
        {
            "command": "pause",
            "accepted": False,
            "rejection_reason": "confirmation_required",
            "event_type": "operational_event",
        },
        {
            "command": "pause",
            "accepted": False,
            "rejection_reason": "confirmation_required",
            "event_type": "operational_event",
        },
        {
            "command": "resume",
            "accepted": True,
            "rejection_reason": None,
            "event_type": "operational_event",
        },
    ]
    filtered = TraderConsoleService.filter_recent_events(events, technical_mode=False)
    assert [event["command"] for event in filtered] == ["pause", "resume"]

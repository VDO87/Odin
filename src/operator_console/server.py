from __future__ import annotations

import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from external_data import ExternalDataAuditLog, ExternalDataService
from intelligence.models import AdvisoryRequest
from intelligence.providers.anythingllm import AnythingLLMProvider
from market import MarketAssessment, MarketOperationalInput
from operator_console.gateway import CommandGateway
from shared.contracts import OperatorCommandRequest
from shared.enums import BlockCode
from shared.utils import parse_datetime, utc_now


WEB_ROOT = Path(__file__).with_name("web")


class TraderConsoleService:
    def __init__(
        self,
        runtime: Any,
        gateway: CommandGateway,
        *,
        config_path: str | Path,
        status_file_path: str | Path | None = None,
    ) -> None:
        self.runtime = runtime
        self.gateway = gateway
        self.config_path = Path(config_path)
        self.settings = runtime.get_settings()
        self.status_file_path = Path(status_file_path) if status_file_path else (
            self.settings.runtime.state_dir / "core_public_view.json"
        )
        self.external_data_service = ExternalDataService(
            self.settings,
            audit_log=ExternalDataAuditLog(
                self.settings.runtime.log_dir / "external-data-audit.jsonl"
            ),
        )
        self._anythingllm_provider = AnythingLLMProvider(config_path=self.config_path)
        self._intelligence_audit_path = self.settings.runtime.log_dir / "intelligence-advisory-audit.jsonl"

    def get_index_html(self) -> str:
        return self._load_web_text("index.html")

    def get_static_asset(self, asset_name: str) -> tuple[bytes, str]:
        asset_path = WEB_ROOT / asset_name
        if not asset_path.exists() or not asset_path.is_file():
            raise FileNotFoundError(asset_name)
        content_type = "text/plain; charset=utf-8"
        if asset_path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif asset_path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif asset_path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        return asset_path.read_bytes(), content_type

    def get_status_payload(self) -> dict[str, Any]:
        self.gateway.record_read_query("status")
        core_view = self.runtime.get_public_view()
        status_file_payload = self._read_status_file_payload()
        status_file_snapshot = self._status_file_snapshot(status_file_payload)
        global_state = (
            str(status_file_snapshot.get("global_state"))
            if status_file_snapshot and status_file_snapshot.get("global_state")
            else core_view.state_code.value
        )
        mode = (
            str(status_file_snapshot.get("mode"))
            if status_file_snapshot and status_file_snapshot.get("mode")
            else core_view.mode_code.value
        )
        readiness = (
            str(status_file_snapshot.get("readiness"))
            if status_file_snapshot and status_file_snapshot.get("readiness")
            else core_view.readiness_class.value
        )
        integrity = (
            str(status_file_snapshot.get("integrity"))
            if status_file_snapshot and status_file_snapshot.get("integrity")
            else core_view.integrity_class.value
        )
        kill_active = (
            bool(status_file_snapshot.get("kill_active"))
            if status_file_snapshot and status_file_snapshot.get("kill_active") is not None
            else core_view.kill_active
        )
        active_block_count = (
            int(status_file_snapshot.get("active_block_count", 0))
            if status_file_snapshot and status_file_snapshot.get("active_block_count") is not None
            else core_view.active_block_vector.active_block_count
        )
        liveness = (
            dict(status_file_snapshot.get("critical_module_liveness", {}))
            if status_file_snapshot
            and isinstance(status_file_snapshot.get("critical_module_liveness"), dict)
            else core_view.critical_module_liveness
        )
        latest_execution = self._read_latest_execution_ledger()
        recent_executions = self._read_recent_execution_ledger(limit=10)
        market_runtime = self.runtime.get_market_runtime_status().to_dict()
        runtime_risk = self.runtime.get_last_risk_assessment() or {}
        runtime_decision = self.runtime.get_last_decision_result() or {}
        runtime_execution = self.runtime.get_last_execution_summary() or {}
        risk_summary = {
            "risk_block_active": (
                runtime_risk.get("risk_decision") in {"BLOCK", "KILL"}
                or core_view.active_block_vector.has_code(BlockCode.RISK)
            ),
            "risk_decision": runtime_risk.get("risk_decision"),
            "risk_state": runtime_risk.get("risk_state"),
            "dominant_block_reason": runtime_risk.get("dominant_risk_reason")
            or core_view.dominant_block_reason,
            "active_block_count": active_block_count,
        }
        decision_last_result = {
            "decision_cycle_id": runtime_decision.get("decision_cycle_id")
            if runtime_decision
            else (latest_execution.get("decision_cycle_id") if latest_execution else None),
            "reason_summary": runtime_decision.get("reason_summary")
            if runtime_decision
            else (latest_execution.get("reason_summary") if latest_execution else None),
            "risk_decision": runtime_risk.get("risk_decision")
            if runtime_risk
            else (latest_execution.get("risk_decision") if latest_execution else None),
            "operational_output": runtime_decision.get("operational_output"),
            "decision_state": runtime_decision.get("decision_state"),
            "decision_output": runtime_decision.get("decision_output"),
            "tactic_id": runtime_decision.get("tactic_id"),
            "score": runtime_decision.get("score"),
            "decision_mode": runtime_decision.get("decision_mode"),
            "intent_id": runtime_decision.get("intent_id"),
            "execution_ledger_ref": (
                (runtime_execution.get("execution_ledger_ref") if runtime_execution else None)
                or (latest_execution.get("ledger_id") if latest_execution else None)
            ),
            "executed_in_demo": (
                latest_execution is not None
                and latest_execution.get("execution_mode") == "MD-20"
                and runtime_decision.get("operational_output") == "CANDIDATE_SELECTED"
            ),
        }
        execution_summary = {
            "last_execution": latest_execution,
            "ledger_available": latest_execution is not None,
            "recent_executions": recent_executions,
            "runtime_last_execution": runtime_execution,
        }
        return {
            "status_source": "core_public_view_file" if status_file_snapshot else "runtime_memory",
            "global_state": global_state,
            "mode": mode,
            "profile": self.settings.profile.name.value,
            "readiness": readiness,
            "integrity": integrity,
            "kill_active": kill_active,
            "active_block_count": active_block_count,
            "active_block_vector": core_view.active_block_vector.to_dict(),
            "last_transition": core_view.last_transition,
            "critical_module_liveness": liveness,
            "liveness": liveness,
            "market_runtime": market_runtime,
            "risk_summary": risk_summary,
            "decision_last_result": decision_last_result,
            "execution_summary": execution_summary,
            "recent_events": self.gateway.recent_logs(),
            "status_file_path": str(self.status_file_path),
            "status_file_present": status_file_payload is not None,
            "status_file_payload": status_file_payload,
            "status_file_snapshot": status_file_snapshot,
        }

    def get_health_payload(self) -> dict[str, Any]:
        self.gateway.record_read_query("health")
        core_view = self.runtime.get_public_view()
        health_metrics = core_view.health_metrics
        liveness = core_view.critical_module_liveness
        return {
            "global_state": core_view.state_code.value,
            "liveness": liveness,
            "liveness_distribution": self.calculate_liveness_distribution(liveness),
            "startup_required_modules": health_metrics.get("startup_required_modules", []),
            "startup_missing_heartbeat_modules": health_metrics.get(
                "startup_missing_heartbeat_modules", []
            ),
            "startup_unavailable_modules": health_metrics.get("startup_unavailable_modules", []),
            "critical_module_timeout_count": health_metrics.get("critical_module_timeout_count", 0),
            "critical_module_delayed_count": health_metrics.get("critical_module_delayed_count", 0),
            "critical_module_ok_count": health_metrics.get("critical_module_ok_count", 0),
            "integrity_class": core_view.integrity_class.value,
            "readiness_class": core_view.readiness_class.value,
        }

    def get_recent_logs_payload(self) -> dict[str, Any]:
        recent_events = self.gateway.recent_logs()
        technical_events = self.gateway.recent_audit_events(limit=120)
        return {
            "recent_events": recent_events,
            "operator_recent_events": self.filter_recent_events(recent_events, technical_mode=False),
            "technical_recent_events": self.filter_recent_events(
                technical_events, technical_mode=True
            ),
        }

    def get_config_payload(self) -> dict[str, Any]:
        result = self.gateway.execute(
            OperatorCommandRequest(
                command="get-config",
                requested_by="console-api",
                role="operator",
            )
        )
        return result.to_dict()

    def get_external_status_payload(self) -> dict[str, Any]:
        self.gateway.record_read_query("external/status")
        return self.external_data_service.get_status_payload()

    def get_external_quote_payload(self, symbol: str) -> dict[str, Any]:
        return self.external_data_service.get_quote_payload(symbol)

    def get_external_calendar_payload(self) -> dict[str, Any]:
        return self.external_data_service.get_calendar_payload()

    def get_external_asset_search_payload(self, query: str) -> dict[str, Any]:
        return self.external_data_service.search_assets_payload(query)

    def post_external_inject_demo_quote_to_market_payload(
        self,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body_payload = dict(body or {})
        quote_payload = self.external_data_service.get_quote_payload("EURUSD")
        quote = dict(quote_payload.get("quote", {}))
        symbol = str(quote.get("symbol", "EURUSD")).strip().upper() or "EURUSD"
        observed_at_utc = self._parse_quote_timestamp(quote)
        now = utc_now()
        max_degraded_age_ms = int(self.settings.market.max_degraded_age_ms)
        sample_age_ms = max(0, int((now - observed_at_utc).total_seconds() * 1000))
        quote_refreshed_before_ingest = False
        if bool(quote.get("from_cache")) and sample_age_ms > max_degraded_age_ms:
            fresh_payload = self.external_data_service.get_quote_payload(
                "EURUSD",
                force_refresh=True,
            )
            fresh_quote = dict(fresh_payload.get("quote", {}))
            fresh_observed_at_utc = self._parse_quote_timestamp(fresh_quote)
            fresh_sample_age_ms = max(
                0,
                int((utc_now() - fresh_observed_at_utc).total_seconds() * 1000),
            )
            if fresh_sample_age_ms <= sample_age_ms:
                quote_payload = fresh_payload
                quote = fresh_quote
                observed_at_utc = fresh_observed_at_utc
                sample_age_ms = fresh_sample_age_ms
                quote_refreshed_before_ingest = True
        bid = quote.get("bid")
        ask = quote.get("ask")
        last_price = quote.get("last_price")
        spread_bps: float | None = None
        if (
            isinstance(bid, (int, float))
            and isinstance(ask, (int, float))
            and isinstance(last_price, (int, float))
            and float(last_price) > 0
        ):
            spread_bps = abs(float(ask) - float(bid)) / float(last_price) * 10_000

        sample = MarketOperationalInput(
            instrument_id=symbol,
            feed_id="primary",
            feed_available=last_price is not None,
            market_open=True,
            sample_valid=last_price is not None,
            sample_age_ms=sample_age_ms,
            latency_ms=50,
            spread_bps=spread_bps,
            news_guard_active=False,
            critical_context_missing=False,
            session_low_activity=False,
            heavy_enrichment_requested=False,
            observed_at_utc=observed_at_utc,
            last_valid_update_utc=observed_at_utc,
        )
        core_view = self.runtime.ingest_market_sample(sample)
        runtime_status = self.runtime.get_market_runtime_status().to_dict()
        market_assessment = self.runtime.get_last_market_assessment()
        market_assessment_state = (
            market_assessment.market_state.value if market_assessment is not None else None
        )
        decision_market_ready = self._is_market_ready_for_decision(
            market_assessment=market_assessment,
            sample_age_ms=sample_age_ms,
        )
        gate_status = str(runtime_status.get("last_gate_status", "idle"))
        accepted = gate_status == "accepted"
        reason = runtime_status.get("last_rejection_reason")
        instrument_id = runtime_status.get("last_instrument_id")
        feed_id = runtime_status.get("last_feed_id")
        source_mode = "cache" if quote.get("from_cache") else "demo"
        if quote.get("provider") and quote.get("provider") != "DemoProvider":
            source_mode = "real"
        requested_by = str(body_payload.get("requested_by", "console-api"))
        role = str(body_payload.get("role", "operator"))
        self.gateway.record_operational_event(
            command="inject-demo-quote-to-market",
            accepted=accepted,
            rejection_reason=str(reason) if reason else None,
            requested_by=requested_by,
            role=role,
        )
        return {
            "accepted": accepted,
            "rejected": not accepted,
            "gate_status": gate_status,
            "reason": reason,
            "reason_code": reason,
            "instrument_id": instrument_id,
            "feed_id": feed_id,
            "runtime": runtime_status,
            "readiness_result": {
                "core_readiness": core_view.readiness_class.value,
                "core_integrity": core_view.integrity_class.value,
                "global_state": core_view.state_code.value,
            },
            "quote": quote,
            "quote_source_mode": source_mode,
            "warnings": list(quote_payload.get("warnings", [])),
            "injected_quote_timestamp": quote.get("timestamp_utc"),
            "ingested_at_utc": sample.observed_at_utc.isoformat(),
            "sample_age_ms": sample_age_ms,
            "max_valid_age_ms": int(self.settings.market.max_valid_age_ms),
            "max_degraded_age_ms": max_degraded_age_ms,
            "market_assessment_state": market_assessment_state,
            "market_assessment_reason_code": (
                market_assessment.reason_code if market_assessment is not None else None
            ),
            "decision_market_ready": decision_market_ready,
            "quote_refreshed_before_ingest": quote_refreshed_before_ingest,
        }

    def post_run_decision_cycle_payload(
        self,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = dict(body or {})
        mode_override = payload.get("mode")
        force_risk_block = bool(payload.get("force_risk_block", False))
        force_market_rejected = bool(payload.get("force_market_rejected", False))
        requested_by = str(payload.get("requested_by", "console-api"))
        result = self.runtime.run_decision_cycle(
            requested_by=requested_by,
            mode_override=str(mode_override) if mode_override is not None else None,
            force_risk_block=force_risk_block,
            force_market_rejected=force_market_rejected,
        )
        self.gateway.record_operational_event(
            command="run-decision-cycle",
            accepted=bool(result.get("accepted", False)),
            rejection_reason=result.get("decision", {}).get("reason_summary")
            if not result.get("accepted", False)
            else None,
            requested_by=requested_by,
            role=str(payload.get("role", "operator")),
        )
        return result

    def post_intelligence_ask_payload(
        self,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = dict(body or {})
        question = str(payload.get("question", "")).strip()
        requested_by = str(payload.get("requested_by", "console-api"))
        role = str(payload.get("role", "operator"))
        if not question:
            response = {
                "accepted": False,
                "rejected": True,
                "reason_code": "question_required",
                "provider": self._anythingllm_provider.name,
                "advisory_only": True,
            }
            self.gateway.record_operational_event(
                command="intelligence/ask",
                accepted=False,
                rejection_reason="question_required",
                requested_by=requested_by,
                role=role,
            )
            self._append_intelligence_audit(
                question=question,
                requested_by=requested_by,
                response=response,
            )
            return response

        if self._is_unsafe_ai_action(question):
            response = {
                "accepted": False,
                "rejected": True,
                "reason_code": "unsafe_ai_action",
                "provider": self._anythingllm_provider.name,
                "advisory_only": True,
            }
            self.gateway.record_operational_event(
                command="intelligence/ask",
                accepted=False,
                rejection_reason="unsafe_ai_action",
                requested_by=requested_by,
                role=role,
            )
            self._append_intelligence_audit(
                question=question,
                requested_by=requested_by,
                response=response,
            )
            return response

        query_scope = self._classify_advisory_scope(question)
        if query_scope == "unsupported":
            response = {
                "accepted": False,
                "rejected": True,
                "reason_code": "unsupported_advisory_query",
                "provider": self._anythingllm_provider.name,
                "advisory_only": True,
                "allowed_scopes": [
                    "explain_current_state",
                    "explain_last_block",
                    "summarize_logs",
                    "explain_last_decision",
                    "search_documentation",
                ],
            }
            self.gateway.record_operational_event(
                command="intelligence/ask",
                accepted=False,
                rejection_reason="unsupported_advisory_query",
                requested_by=requested_by,
                role=role,
            )
            self._append_intelligence_audit(
                question=question,
                requested_by=requested_by,
                response=response,
            )
            return response

        advisory_request = AdvisoryRequest(
            question=question,
            requested_by=requested_by,
            query_scope=query_scope,
        )
        context_payload = self._build_intelligence_context(query_scope)
        advisory_response = self._anythingllm_provider.ask(
            advisory_request,
            context_payload=context_payload,
        )
        response = {
            **advisory_response.to_dict(),
            "query_scope": query_scope,
            "warning": "Advisory only",
            "state_mutation": "not_allowed",
            "can_execute_orders": False,
            "can_change_core_state": False,
        }
        rejection_reason = None
        if not response.get("accepted", False):
            reason_raw = response.get("reason_code")
            rejection_reason = str(reason_raw) if reason_raw else None
        self.gateway.record_operational_event(
            command="intelligence/ask",
            accepted=bool(response.get("accepted", False)),
            rejection_reason=rejection_reason,
            requested_by=requested_by,
            role=role,
        )
        self._append_intelligence_audit(
            question=question,
            requested_by=requested_by,
            response=response,
        )
        return response

    def post_command_payload(
        self,
        command: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = body or {}
        request = OperatorCommandRequest(
            command=command,
            requested_by=str(payload.get("requested_by", "console-api")),
            role=str(payload.get("role", "operator")),
            confirmation=bool(payload.get("confirmation", False)),
            authorization_context=dict(payload.get("authorization_context", {"ticket": "console-api"})),
            payload=dict(payload.get("payload", {})),
        )
        response = self.gateway.execute(request).to_dict()
        response["reason_code"] = response.get("rejection_reason")
        return response

    def post_export_logs_payload(self, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(body or {})
        command_payload = dict(payload.get("payload", {}))
        if "export_path" in payload and "export_path" not in command_payload:
            command_payload["export_path"] = payload["export_path"]
        request = OperatorCommandRequest(
            command="export-logs",
            requested_by=str(payload.get("requested_by", "console-api")),
            role=str(payload.get("role", "operator")),
            authorization_context=dict(payload.get("authorization_context", {"ticket": "console-api"})),
            payload=command_payload,
        )
        response = self.gateway.execute(request).to_dict()
        response["reason_code"] = response.get("rejection_reason")
        return response

    def _load_web_text(self, asset_name: str) -> str:
        return (WEB_ROOT / asset_name).read_text(encoding="utf-8")

    def _read_status_file_payload(self) -> dict[str, Any] | None:
        if not self.status_file_path.exists():
            return None
        try:
            raw = json.loads(self.status_file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return raw if isinstance(raw, dict) else None

    @staticmethod
    def _status_file_snapshot(payload: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        return {
            "global_state": payload.get("state_code"),
            "mode": payload.get("mode_code"),
            "readiness": payload.get("readiness_class"),
            "integrity": payload.get("integrity_class"),
            "kill_active": payload.get("kill_active"),
            "active_block_count": payload.get("active_block_count"),
            "critical_module_liveness": payload.get("critical_module_liveness"),
            "last_transition": payload.get("last_transition"),
        }

    def _read_latest_execution_ledger(self) -> dict[str, Any] | None:
        store = self.runtime.get_state_store()
        record = store.read_latest_execution_ledger_record()
        if record is None:
            return None
        return record.to_dict()

    def _read_recent_execution_ledger(self, *, limit: int) -> list[dict[str, Any]]:
        store = self.runtime.get_state_store()
        records = store.list_execution_ledger_records()
        if not records:
            return []
        payload = [record.to_dict() for record in records]
        return payload[-limit:]

    def _build_intelligence_context(self, query_scope: str) -> dict[str, Any]:
        context: dict[str, Any] = {
            "status": self.get_status_payload(),
            "health": self.get_health_payload(),
            "recent_events": self.get_recent_logs_payload().get("operator_recent_events", []),
            "advisory_constraints": {
                "advisory_only": True,
                "cannot_execute_orders": True,
                "cannot_clear_blocks": True,
                "cannot_change_mode_without_human_confirmation": True,
            },
        }
        if query_scope == "search_documentation":
            context["documentation_hints"] = {
                "readme": "README.md",
                "runbook": "docs/runbooks/ODIN-RUNBOOK-v0.1.md",
                "console_testing": "docs/runbooks/ODIN-TRADER-CONSOLE-TESTING.md",
                "traceability": "docs/traceability/ODIN-TRACEABILITY-MATRIX.md",
            }
        return context

    @staticmethod
    def _is_unsafe_ai_action(question: str) -> bool:
        normalized = question.casefold()
        blocked_terms = (
            "compra",
            "vende",
            "limpa kill",
            "muda para real",
            "aumenta risco",
        )
        return any(term in normalized for term in blocked_terms)

    @staticmethod
    def _classify_advisory_scope(question: str) -> str:
        normalized = question.casefold()
        mapping = {
            "explain_current_state": ("estado atual", "status atual", "estado", "status", "state"),
            "explain_last_block": ("bloqueio", "último bloqueio", "ultimo bloqueio", "block", "kill"),
            "summarize_logs": ("resumir logs", "logs", "eventos", "events", "timeline"),
            "explain_last_decision": ("última decisão", "ultima decisao", "decisão", "decision", "intent"),
            "search_documentation": ("documentação", "documentacao", "docs", "runbook", "readme", "sds"),
        }
        for scope, terms in mapping.items():
            if any(term in normalized for term in terms):
                return scope
        return "unsupported"

    def _append_intelligence_audit(
        self,
        *,
        question: str,
        requested_by: str,
        response: dict[str, Any],
    ) -> None:
        record = {
            "ts_utc": utc_now().isoformat(),
            "event": "intelligence_advisory",
            "requested_by": requested_by,
            "question": question,
            "response": response,
        }
        self._intelligence_audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self._intelligence_audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    @staticmethod
    def _parse_quote_timestamp(quote: dict[str, Any]) -> datetime:
        timestamp_raw = quote.get("timestamp_utc")
        if timestamp_raw:
            try:
                parsed = parse_datetime(str(timestamp_raw))
                if parsed is not None:
                    return parsed
            except ValueError:
                pass
        return utc_now()

    def _is_market_ready_for_decision(
        self,
        *,
        market_assessment: MarketAssessment | None,
        sample_age_ms: int,
    ) -> bool:
        if market_assessment is None:
            return False
        if self.runtime.get_market_runtime_status().last_gate_status != "accepted":
            return False
        if sample_age_ms > int(self.settings.market.max_degraded_age_ms):
            return False
        if market_assessment.market_state.value in {"MS-30", "MS-40", "MS-50"}:
            return False
        if market_assessment.readiness_state.value in {"NOT_READY", "UNAVAILABLE"}:
            return False
        if market_assessment.feed_integrity_state.value in {"FI-30", "FI-40"}:
            return False
        if market_assessment.context_state.value == "MC-40":
            return False
        return True

    @staticmethod
    def calculate_liveness_distribution(liveness: dict[str, str]) -> dict[str, int]:
        distribution = {"ok": 0, "degraded": 0, "unavailable": 0, "nodata": 0}
        if not liveness:
            distribution["nodata"] = 1
            return distribution
        for status in liveness.values():
            if status == "OK":
                distribution["ok"] += 1
            elif status in {"DELAYED", "NOT_STARTED"}:
                distribution["degraded"] += 1
            elif status in {"TIMEOUT", "UNAVAILABLE"}:
                distribution["unavailable"] += 1
            else:
                distribution["degraded"] += 1
        return distribution

    @staticmethod
    def filter_recent_events(
        events: list[dict[str, Any]],
        *,
        technical_mode: bool,
    ) -> list[dict[str, Any]]:
        if technical_mode:
            return events[-40:]
        filtered: list[dict[str, Any]] = []
        previous: dict[str, Any] | None = None
        for event in events:
            event_type = str(event.get("event_type", "operational_event")).strip().lower()
            if event_type == "read_query":
                continue
            if (
                previous is not None
                and previous.get("command") == event.get("command")
                and previous.get("accepted") == event.get("accepted")
                and previous.get("rejection_reason") == event.get("rejection_reason")
            ):
                continue
            filtered.append(event)
            previous = event
        return filtered[-20:]


class TraderConsoleHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], service: TraderConsoleService) -> None:
        self.service = service
        super().__init__(server_address, _build_handler())


def serve_operator_console(
    service: TraderConsoleService,
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> TraderConsoleHTTPServer:
    return TraderConsoleHTTPServer((host, port), service)


def _build_handler() -> type[BaseHTTPRequestHandler]:
    class _Handler(BaseHTTPRequestHandler):
        server: TraderConsoleHTTPServer

        def do_GET(self) -> None:  # noqa: N802
            try:
                parsed = urlparse(self.path)
                path = parsed.path
                query_params = parse_qs(parsed.query)
                if path in {"/", "/index.html"}:
                    self._html_response(self.server.service.get_index_html())
                    return
                if path == "/style.css":
                    self._asset_response("style.css")
                    return
                if path == "/app.js":
                    self._asset_response("app.js")
                    return
                if path == "/api/status":
                    self._json_response(self.server.service.get_status_payload())
                    return
                if path == "/api/health":
                    self._json_response(self.server.service.get_health_payload())
                    return
                if path == "/api/logs/recent":
                    self._json_response(self.server.service.get_recent_logs_payload())
                    return
                if path == "/api/config":
                    self._json_response(self.server.service.get_config_payload())
                    return
                if path == "/api/external/status":
                    self._json_response(self.server.service.get_external_status_payload())
                    return
                if path == "/api/external/quote":
                    symbol = str(query_params.get("symbol", ["EURUSD"])[0])
                    self._json_response(self.server.service.get_external_quote_payload(symbol))
                    return
                if path == "/api/external/calendar":
                    self._json_response(self.server.service.get_external_calendar_payload())
                    return
                if path == "/api/external/assets/search":
                    query = str(query_params.get("q", [""])[0])
                    self._json_response(self.server.service.get_external_asset_search_payload(query))
                    return
                self._json_response({"error": "not_found"}, status_code=404)
            except Exception as error:
                self._json_response(
                    {
                        "error": "internal_error",
                        "reason_code": "operator_console_get_failed",
                        "reason_text": f"{error.__class__.__name__}: {error}",
                    },
                    status_code=500,
                )

        def do_POST(self) -> None:  # noqa: N802
            try:
                parsed = urlparse(self.path)
                path = parsed.path
                body = self._read_body_json()
                if path == "/api/commands/pause":
                    self._json_response(self.server.service.post_command_payload("pause", body))
                    return
                if path == "/api/commands/resume":
                    self._json_response(self.server.service.post_command_payload("resume", body))
                    return
                if path == "/api/commands/stop":
                    self._json_response(self.server.service.post_command_payload("stop", body))
                    return
                if path == "/api/logs/export":
                    self._json_response(self.server.service.post_export_logs_payload(body))
                    return
                if path == "/api/external/inject-demo-quote-to-market":
                    self._json_response(
                        self.server.service.post_external_inject_demo_quote_to_market_payload(body)
                    )
                    return
                if path == "/api/test/run-decision-cycle":
                    self._json_response(self.server.service.post_run_decision_cycle_payload(body))
                    return
                if path == "/api/intelligence/ask":
                    self._json_response(self.server.service.post_intelligence_ask_payload(body))
                    return
                self._json_response({"error": "not_found"}, status_code=404)
            except Exception as error:
                self._json_response(
                    {
                        "error": "internal_error",
                        "reason_code": "operator_console_post_failed",
                        "reason_text": f"{error.__class__.__name__}: {error}",
                    },
                    status_code=500,
                )

        def _asset_response(self, asset_name: str) -> None:
            try:
                payload, content_type = self.server.service.get_static_asset(asset_name)
            except FileNotFoundError:
                self._json_response({"error": "not_found"}, status_code=404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, _format: str, *_args: object) -> None:
            return

        def _read_body_json(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                return {}
            raw = self.rfile.read(content_length)
            if not raw:
                return {}
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return {}
            if not isinstance(payload, dict):
                return {}
            return payload

        def _json_response(self, payload: dict[str, Any], *, status_code: int = 200) -> None:
            encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _html_response(self, html: str) -> None:
            encoded = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return _Handler

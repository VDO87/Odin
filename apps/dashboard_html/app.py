from __future__ import annotations

import ast
import argparse
import html
import json
import os
import subprocess
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from odin_assistant.assistant_router import AssistantRouter
from odin_atlas.coordinator import AtlasCoordinator
from odin_control.system_controller import SystemController
from odin_core.runtime_validator import log_runtime_validation, validate_runtime_artifacts
from odin_dashboard.formatters import (
    group_repeated_events,
    heartbeat_age_seconds,
    render_html_sparkline,
    short_ts,
)
from odin_dashboard.state_provider import DashboardStateProvider
from odin_health.healthcheck import OdinHealthcheck


@dataclass(slots=True)
class DashboardResponse:
    status_code: int
    content_type: str
    body: bytes


def _detect_version() -> str:
    env_version = os.getenv("ODIN_DASHBOARD_VERSION", "").strip()
    if env_version:
        return env_version
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            check=False,
            timeout=1,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "RC1.6.1"


class DashboardApp:
    def __init__(self) -> None:
        self.controller = SystemController(log_root="logs")
        self.atlas = AtlasCoordinator(log_root="logs")
        self.assistant = AssistantRouter(self.controller)
        self.provider = DashboardStateProvider(log_root="logs")
        self.templates = Path("apps/dashboard_html/templates")
        self.static = Path("apps/dashboard_html/static")
        self.version = _detect_version()

    @staticmethod
    def _display_value(value: object, *, default: str = "n/a") -> str:
        if value is None:
            return default
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return default
            if stripped.lower() == "none":
                return default
            return stripped
        if isinstance(value, list):
            if not value:
                return default
            return ", ".join(str(item) for item in value)
        if isinstance(value, dict):
            if not value:
                return default
            return json.dumps(value, sort_keys=True, ensure_ascii=False)
        return str(value)

    def _humanize_answer(self, answer: object) -> str:
        if answer is None:
            return "Não existem dados suficientes para responder com segurança."
        if isinstance(answer, dict):
            rows = [f"{key}: {self._display_value(value, default='unavailable')}" for key, value in answer.items()]
            return "; ".join(rows) if rows else "Não existem dados suficientes para responder com segurança."
        if isinstance(answer, list):
            if not answer:
                return "Não existem dados suficientes para responder com segurança."
            return "; ".join(self._display_value(item, default="unavailable") for item in answer)
        text = str(answer).strip()
        if not text:
            return "Não existem dados suficientes para responder com segurança."
        if text.startswith("{'") and text.endswith("}"):
            try:
                parsed = ast.literal_eval(text)
            except (SyntaxError, ValueError):
                return text
            return self._humanize_answer(parsed)
        return text

    def _json(self, payload: dict[str, object], code: int = 200) -> DashboardResponse:
        return DashboardResponse(
            status_code=code,
            content_type="application/json; charset=utf-8",
            body=json.dumps(payload, sort_keys=True, default=str).encode("utf-8"),
        )

    def _text(
        self,
        payload: str,
        *,
        content_type: str = "text/html; charset=utf-8",
        code: int = 200,
    ) -> DashboardResponse:
        return DashboardResponse(status_code=code, content_type=content_type, body=payload.encode("utf-8"))

    def _render_template(self, name: str, replacements: dict[str, str]) -> str:
        path = self.templates / name
        source = path.read_text(encoding="utf-8")
        for key, value in replacements.items():
            source = source.replace("{{" + key + "}}", value)
        return source

    def _render_base(self, title: str, content: str) -> str:
        return self._render_template("base.html", {"title": title, "content": content})

    def _rows(self, pairs: list[tuple[str, object]]) -> str:
        out = []
        for key, value in pairs:
            out.append(
                '<div class="kv">'
                f'<div class="k">{html.escape(str(key))}</div>'
                f'<div class="v">{html.escape(self._display_value(value, default="unavailable"))}</div>'
                "</div>"
            )
        return "".join(out)

    def _as_log_lines(self, rows: list[dict[str, object]], *, limit: int = 12) -> str:
        grouped = group_repeated_events(rows[-max(1, limit * 4) :])
        lines: list[str] = []
        for item in grouped[-limit:]:
            ts = short_ts(str(item.get("last_timestamp") or item.get("timestamp") or ""))
            event_type = str(item.get("event_type", "EVENT"))
            message = str(item.get("message", ""))
            count = int(item.get("count", 1))
            suffix = f" x{count}" if count > 1 else ""
            rendered = f"[{ts}] {event_type}{suffix} {message}".strip()
            escaped = html.escape(rendered)

            event_up = event_type.upper()
            if event_up in {"ERROR", "ORDER_ATTEMPT"}:
                lines.append(f'<span class="critical-line">{escaped}</span>')
            elif event_up == "COMMAND_BLOCKED":
                lines.append(f'<span class="blocked-line">{escaped}</span>')
            else:
                lines.append(escaped)
        return "\n".join(lines) if lines else "no data"

    def _state(self) -> dict[str, object]:
        force_demo = os.getenv("ODIN_DASHBOARD_FORCE_DEMO", "false").lower() == "true"
        return self.provider.load_state(force_demo=force_demo)

    def _system_block(self, state: dict[str, object]) -> str:
        runtime = state.get("runtime", {}) if isinstance(state.get("runtime"), dict) else {}
        soak = state.get("soak", {}) if isinstance(state.get("soak"), dict) else {}
        validate = state.get("runtime_validate", {}) if isinstance(state.get("runtime_validate"), dict) else {}
        hb = str(runtime.get("heartbeat", ""))
        hb_age = heartbeat_age_seconds(hb)
        return self._rows(
            [
                ("Mode", state.get("mode", "SHADOW_MT5")),
                ("Runtime State", state.get("runtime_state", runtime.get("state", "UNKNOWN"))),
                ("Trading Permission", state.get("trading_permission_state", "BLOCKED")),
                ("Health State", state.get("system_health_state", runtime.get("health_status", "UNKNOWN"))),
                ("safe_to_trade", state.get("safe_to_trade", runtime.get("safe_to_trade", False))),
                ("Heartbeat ts", hb or "unavailable"),
                ("Heartbeat age", f"{hb_age}s" if hb_age is not None else "n/a"),
                ("Soak", soak.get("result", "n/a")),
                ("Runtime validate", validate.get("status", runtime.get("runtime_validate", "n/a"))),
                ("Uptime", runtime.get("uptime_seconds", "n/a")),
            ]
        )

    def _market_block(self, state: dict[str, object]) -> str:
        mt5 = state.get("mt5", {}) if isinstance(state.get("mt5"), dict) else {}
        mt5_tick = mt5.get("tick", {}) if isinstance(mt5.get("tick"), dict) else {}
        series = mt5.get("sparkline", []) if isinstance(mt5.get("sparkline"), list) else []
        chart = render_html_sparkline(series)
        chart_label = "DEMO DATA" if state.get("demo_data", False) else mt5.get("chart_label", "LIVE")
        rows = self._rows(
            [
                ("Symbol", mt5.get("symbol", "EURUSD")),
                ("Timeframe", mt5.get("timeframe", "M15")),
                ("Bid", mt5_tick.get("bid", "n/a")),
                ("Ask", mt5_tick.get("ask", "n/a")),
                ("Spread", mt5_tick.get("spread", "n/a")),
                ("MT5 status", mt5.get("status", "UNKNOWN")),
            ]
        )
        return (
            rows
            + '<div class="kv"><div class="k">SPARKLINE</div>'
            f'<div class="v">{chart} <span class="small">{html.escape(str(chart_label))}</span></div></div>'
        )

    def _intel_block(self, state: dict[str, object]) -> str:
        intel = state.get("market_intelligence", {}) if isinstance(state.get("market_intelligence"), dict) else {}
        events = intel.get("high_impact_events", []) if isinstance(intel.get("high_impact_events"), list) else []
        rows = self._rows(
            [
                ("News status", intel.get("news_status", "UNAVAILABLE")),
                ("Macro calendar", intel.get("macro_calendar_status", "UNAVAILABLE")),
                ("Sentiment", intel.get("sentiment_summary", "neutral")),
                ("Blocked by news", intel.get("blocked_by_news", False)),
            ]
        )
        event_text = "\n".join([f"- {html.escape(str(item))}" for item in events[:4]]) or "- none"
        return rows + f'<pre class="logbox">{event_text}</pre>'

    def _atlas_block(self, state: dict[str, object]) -> str:
        atlas = state.get("atlas", {}) if isinstance(state.get("atlas"), dict) else {}
        profile = state.get("atlas_profile", {}) if isinstance(state.get("atlas_profile"), dict) else {}
        agents = atlas.get("agents", {}) if isinstance(atlas.get("agents"), dict) else {}
        decision_packet = atlas.get("decision_packet", {}) if isinstance(atlas.get("decision_packet"), dict) else {}
        return self._rows(
            [
                ("Profile", profile.get("profile", atlas.get("profile", "lite"))),
                ("Consensus", atlas.get("consensus", decision_packet.get("consensus_score", "unavailable"))),
                ("Data quality", atlas.get("data_quality", "unavailable")),
                ("Market agent", agents.get("market_agent", atlas.get("market_agent_score", "unavailable"))),
                ("Technical agent", agents.get("technical_agent", atlas.get("technical_agent_score", "unavailable"))),
                ("News agent", agents.get("news_agent", atlas.get("news_agent_score", "unavailable"))),
                ("Risk agent", agents.get("risk_agent", atlas.get("risk_agent_result", "warning"))),
                ("Critic", agents.get("critic_agent", atlas.get("critic_agent_result", "warning"))),
                ("Execution permission", atlas.get("execution_permission", "SHADOW_ONLY")),
            ]
        )

    def _risk_block(self, state: dict[str, object]) -> str:
        risk = state.get("risk", {}) if isinstance(state.get("risk"), dict) else {}
        blocked_reasons = risk.get("blocked_reasons", "No active risk block detected")
        if isinstance(blocked_reasons, list):
            blocked_reasons = ", ".join(str(item) for item in blocked_reasons) if blocked_reasons else "No active risk block detected"
        return self._rows(
            [
                ("Status", risk.get("status", "ACTIVE")),
                ("Risk per trade", risk.get("max_risk_per_trade_percent", "0.25")),
                ("Max daily loss", risk.get("max_daily_loss_percent", "1.00")),
                ("Trades today", risk.get("trades_today", 0)),
                ("Max trades/day", risk.get("max_trades_per_day", 5)),
                ("Consecutive losses", risk.get("consecutive_losses", 0)),
                ("Blocked reasons", blocked_reasons),
                ("safe_to_trade", risk.get("safe_to_trade", False)),
            ]
        )

    def _positions_block(self, state: dict[str, object]) -> str:
        positions = state.get("positions", {}) if isinstance(state.get("positions"), dict) else {}
        rec: dict[str, object] = {}
        rec_source = positions.get("reconciliation")
        if isinstance(rec_source, dict):
            rec_data = rec_source.get("data", {})
            if isinstance(rec_data, dict):
                maybe = rec_data.get("reconciliation", {})
                if isinstance(maybe, dict):
                    rec = maybe
        if not rec and isinstance(positions, dict):
            rec = positions
        return self._rows(
            [
                ("Total", rec.get("total_positions", positions.get("total", 0))),
                ("ODIN managed", rec.get("odin_managed", rec.get("odin_managed_positions", 0))),
                ("External", rec.get("external_positions", positions.get("external", 0))),
                ("Unprotected", rec.get("unprotected_positions", positions.get("unprotected", 0))),
                ("Unknown magic", rec.get("unknown_magic", positions.get("unknown_magic", 0))),
                ("Reconciliation", rec.get("recommended_state", positions.get("reconciliation", "n/a"))),
                ("Recommended state", rec.get("recommended_state", "n/a")),
            ]
        )

    def _assistant_state_block(self, state: dict[str, object]) -> str:
        assistant = state.get("assistant", {}) if isinstance(state.get("assistant"), dict) else {}
        llm = state.get("llm", {}) if isinstance(state.get("llm"), dict) else {}
        readable_answer = self._humanize_answer(
            assistant.get("last_answer", assistant.get("answer", "No assistant response available"))
        )
        return self._rows(
            [
                ("Última pergunta", assistant.get("last_question", assistant.get("question", "n/a"))),
                ("Última resposta", readable_answer),
                ("Source", assistant.get("source", "fallback")),
                ("LLM status", llm.get("status", "WARNING")),
                ("LLM provider", llm.get("provider", "ollama")),
                ("LLM model", llm.get("model", "")),
            ]
        )

    def _index_content(self) -> str:
        state = self._state()
        runtime = state.get("runtime", {}) if isinstance(state.get("runtime"), dict) else {}
        events = state.get("events", []) if isinstance(state.get("events"), list) else []

        mode = str(state.get("mode", "SHADOW_MT5"))
        runtime_state = self._display_value(state.get("runtime_state", runtime.get("state", "UNKNOWN")), default="UNKNOWN")
        trading_permission_state = self._display_value(state.get("trading_permission_state", "BLOCKED"), default="BLOCKED")
        health_state = self._display_value(state.get("system_health_state", runtime.get("health_status", "UNKNOWN")), default="UNKNOWN")
        hb_age = heartbeat_age_seconds(str(runtime.get("heartbeat", "")))
        safe_to_trade = state.get("safe_to_trade", runtime.get("safe_to_trade", False))
        demo_label = "DEMO DATA" if bool(state.get("demo_data", False)) else "LIVE SNAPSHOT"
        alerts = f"{demo_label} | Runtime={runtime_state} | safe_to_trade={safe_to_trade}"

        content = self._render_template(
            "index.html",
            {
                "mode": html.escape(mode),
                "runtime_state": html.escape(runtime_state),
                "trading_permission_state": html.escape(trading_permission_state),
                "health_state": html.escape(health_state),
                "safe_to_trade": html.escape(str(safe_to_trade)),
                "heartbeat_age": html.escape(str(hb_age if hb_age is not None else "n/a")),
                "version": html.escape(self.version),
                "demo_label": html.escape(demo_label),
                "alerts": html.escape(alerts),
                "system_block": self._system_block(state),
                "market_block": self._market_block(state),
                "intel_block": self._intel_block(state),
                "atlas_block": self._atlas_block(state),
                "risk_block": self._risk_block(state),
                "positions_block": self._positions_block(state),
                "assistant_block": self._assistant_state_block(state),
                "events_block": f'<pre class="logbox">{self._as_log_lines(events, limit=14)}</pre>',
            },
        )
        return self._render_base("ODIN Dashboard", content)

    def _runtime_content(self) -> str:
        state = self._state()
        validation = validate_runtime_artifacts()
        log_runtime_validation(validation)
        soak = state.get("soak", {}) if isinstance(state.get("soak"), dict) else {}

        runtime = state.get("runtime", {}) if isinstance(state.get("runtime"), dict) else {}
        runtime_block = self._rows(
            [
                ("Runtime State", state.get("runtime_state", runtime.get("state", "UNKNOWN"))),
                ("Trading Permission", state.get("trading_permission_state", runtime.get("trading_permission_state", "BLOCKED"))),
                ("Health State", state.get("system_health_state", runtime.get("health_status", "UNKNOWN"))),
                ("Heartbeat", short_ts(str(runtime.get("heartbeat", "")))),
                ("Heartbeat age", heartbeat_age_seconds(str(runtime.get("heartbeat", ""))) or "n/a"),
                ("Safe to trade", runtime.get("safe_to_trade", False)),
                ("Demo", state.get("demo_data", False)),
            ]
        )
        validation_block = f'<pre class="logbox">{html.escape(json.dumps(validation, indent=2, sort_keys=True))}</pre>'
        soak_block = f'<pre class="logbox">{html.escape(json.dumps(soak, indent=2, sort_keys=True))}</pre>'
        content = self._render_template(
            "runtime.html",
            {
                "runtime_block": runtime_block,
                "validation_block": validation_block,
                "soak_block": soak_block,
            },
        )
        return self._render_base("ODIN Runtime", content)

    def _mt5_content(self) -> str:
        state = self._state()
        mt5 = state.get("mt5", {}) if isinstance(state.get("mt5"), dict) else {}
        events = state.get("events", []) if isinstance(state.get("events"), list) else []
        mt5_block = f'<pre class="logbox">{html.escape(json.dumps(mt5, indent=2, sort_keys=True, default=str))}</pre>'
        events_block = f'<pre class="logbox">{self._as_log_lines(events, limit=12)}</pre>'
        content = self._render_template("mt5.html", {"mt5_block": mt5_block, "events_block": events_block})
        return self._render_base("ODIN MT5", content)

    def _atlas_content(self) -> str:
        state = self._state()
        atlas = state.get("atlas", {}) if isinstance(state.get("atlas"), dict) else {}
        profile = state.get("atlas_profile", {}) if isinstance(state.get("atlas_profile"), dict) else {}
        atlas_block = f'<pre class="logbox">{html.escape(json.dumps(atlas, indent=2, sort_keys=True, default=str))}</pre>'
        atlas_profile_block = (
            f'<pre class="logbox">{html.escape(json.dumps(profile, indent=2, sort_keys=True, default=str))}</pre>'
        )
        content = self._render_template(
            "atlas.html",
            {"atlas_block": atlas_block, "atlas_profile_block": atlas_profile_block},
        )
        return self._render_base("ODIN ATLAS", content)

    def _assistant_content(self) -> str:
        llm = self.assistant.llm_status()
        ask_block = (
            '<div class="input-line"><input id="q" placeholder="Qual é o estado do ODIN?">'
            '<button class="btn" onclick="askNow()">Perguntar</button></div>'
            '<pre id="aout" class="logbox"></pre>'
            '<div class="small">Detalhes técnicos</div>'
            '<pre id="adetails" class="logbox"></pre>'
            '<script>async function askNow(){const q=document.getElementById("q").value||"Qual é o estado do ODIN?";'
            'const r=await fetch("/assistant/ask?q="+encodeURIComponent(q));const d=await r.json();'
            'document.getElementById("aout").textContent=d.answer_human||d.answer||"Sem resposta";'
            'document.getElementById("adetails").textContent=JSON.stringify(d,null,2);}</script>'
        )
        assistant_block = f'<pre class="logbox">{html.escape(json.dumps(llm, indent=2, sort_keys=True))}</pre>'
        content = self._render_template(
            "assistant.html",
            {"assistant_block": assistant_block, "ask_block": ask_block},
        )
        return self._render_base("ODIN Assistant", content)

    def _logs_content(self) -> str:
        state = self._state()
        events = state.get("events", []) if isinstance(state.get("events"), list) else []
        errors = state.get("errors", []) if isinstance(state.get("errors"), list) else []
        events_block = f'<pre class="logbox">{self._as_log_lines(events, limit=30)}</pre>'
        errors_block = f'<pre class="logbox">{self._as_log_lines(errors, limit=30)}</pre>'
        content = self._render_template("logs.html", {"events_block": events_block, "errors_block": errors_block})
        return self._render_base("ODIN Logs", content)

    def _assistant_payload(self, question: str) -> dict[str, object]:
        payload = self.assistant.ask(question, channel="dashboard")
        payload["answer_human"] = self._humanize_answer(payload.get("answer"))
        return payload

    def export_preview(self) -> dict[str, object]:
        preview_dir = Path(os.getenv("ODIN_DASHBOARD_PREVIEW_DIR", "dashboard_preview"))
        preview_dir.mkdir(parents=True, exist_ok=True)
        pages = {
            "index.html": "/",
            "runtime.html": "/runtime",
            "mt5.html": "/mt5",
            "atlas.html": "/atlas",
            "assistant.html": "/assistant",
            "logs.html": "/logs",
        }
        written: list[str] = []
        for filename, route in pages.items():
            response = self.handle("GET", route)
            if response.status_code < 400:
                (preview_dir / filename).write_bytes(response.body)
                written.append(filename)
        (preview_dir / "README_PREVIEW.md").write_text(
            "# Dashboard Preview\n\nGerado por `python -m apps.dashboard_html.app --export-preview`.\n",
            encoding="utf-8",
        )
        written.append("README_PREVIEW.md")
        return {"status": "ok", "preview_dir": str(preview_dir), "files": written}

    def dashboard_qa(self) -> dict[str, object]:
        self.export_preview()
        required_paths = ["/", "/runtime", "/mt5", "/atlas", "/assistant", "/llm/status", "/logs"]
        checks: list[dict[str, object]] = []
        failures: list[str] = []
        for route in required_paths:
            response = self.handle("GET", route)
            ok = response.status_code < 400
            checks.append({"route": route, "status_code": response.status_code, "ok": ok})
            if not ok:
                failures.append(f"route:{route}")

        state = self._state()
        index = self.handle("GET", "/").body.decode("utf-8", errors="ignore")
        critical_tokens = [
            "TRADING REAL: BLOCKED",
            "MT5 ORDER_SEND: BLOCKED",
            "BROKER REAL: BLOCKED",
            "ATLAS: SHADOW_ONLY",
            "LLM: READ_ONLY",
            "Perguntar ao ODIN",
            "TRADING PERMISSION",
            "RUNTIME STATE",
            "HEALTH STATE",
            "RISK ENGINE",
            "POSITIONS",
            "EVENTS",
            "ASSISTANT",
            "COMMAND BAR",
            "SPARKLINE",
            "MARKET INTELLIGENCE",
        ]
        if state.get("demo_data", False):
            critical_tokens.append("DEMO DATA")

        forbidden_tokens = [
            "ENABLE_REAL_TRADING",
            "DIRECT_ORDER_SEND",
            "BROKER_REAL_EXECUTION",
            "Activa trading real",
            "Abrir ordem",
            "Fechar posição",
            "{'state':",
            "sparkline n/a",
            ">none<",
        ]
        token_checks = []
        for token in critical_tokens:
            present = token.upper() in index.upper()
            token_checks.append({"token": token, "present": present})
            if not present:
                failures.append(f"token:{token}")
        for token in forbidden_tokens:
            present = token.upper() in index.upper()
            token_checks.append({"token": f"forbidden::{token}", "present": present})
            if present:
                failures.append(f"forbidden:{token}")
        if "None" in index:
            token_checks.append({"token": "forbidden::None", "present": True})
            failures.append("forbidden:None")
        else:
            token_checks.append({"token": "forbidden::None", "present": False})

        report = {
            "status": "PASS" if not failures else "FAIL",
            "checks": checks,
            "tokens": token_checks,
            "failures": failures,
        }
        report_path = Path("docs/reports/ODIN_DASHBOARD_VISUAL_QA_REPORT.md")
        lines = ["# ODIN Dashboard Visual QA Report", "", f"- Status: **{report['status']}**", ""]
        lines.append("## Endpoint Checks")
        for item in checks:
            lines.append(f"- {item['route']}: {item['status_code']} ok={item['ok']}")
        lines.append("")
        lines.append("## Critical Tokens")
        for item in token_checks:
            lines.append(f"- {item['token']}: present={item['present']}")
        if failures:
            lines.append("")
            lines.append("## Failures")
            for failure in failures:
                lines.append(f"- {failure}")
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return report

    def handle(self, method: str, raw_path: str) -> DashboardResponse:
        parsed = urlparse(raw_path)
        qs = parse_qs(parsed.query)

        if method == "GET" and parsed.path == "/":
            return self._text(self._index_content())

        if method == "GET" and parsed.path == "/runtime":
            return self._text(self._runtime_content())

        if method == "GET" and parsed.path == "/mt5":
            return self._text(self._mt5_content())

        if method == "GET" and parsed.path == "/atlas":
            return self._text(self._atlas_content())

        if method == "GET" and parsed.path == "/assistant":
            return self._text(self._assistant_content())

        if method == "GET" and parsed.path == "/logs":
            return self._text(self._logs_content())

        if method == "GET" and parsed.path == "/static/odin_terminal.css":
            css = (self.static / "odin_terminal.css").read_text(encoding="utf-8")
            return self._text(css, content_type="text/css; charset=utf-8")

        if method == "GET" and parsed.path in {"/assistant/ask", "/api/ask"}:
            question = qs.get("q", [""])[0]
            return self._json(self._assistant_payload(question))

        if method == "POST" and parsed.path == "/assistant/ask":
            question = qs.get("q", [""])[0]
            return self._json(self._assistant_payload(question))

        if method == "GET" and parsed.path == "/llm/status":
            return self._json(self.assistant.llm_status())

        if method == "GET" and parsed.path == "/runtime/validate":
            result = validate_runtime_artifacts()
            log_runtime_validation(result)
            return self._json(result)

        if method == "GET" and parsed.path == "/runtime/soak/latest":
            state = self._state()
            return self._json({"soak": state.get("soak", {}), "demo_data": state.get("demo_data", False)})

        if method == "POST" and parsed.path == "/runtime/soak/mini":
            confirm = qs.get("confirm", ["false"])[0].lower() == "true"
            if not confirm:
                return self._json({"accepted": False, "reason": "confirmation_required"}, code=400)
            result = self.controller.execute("RUNTIME_RUN_ONCE", actor="dashboard", role="operator")
            return self._json(result)

        if method == "GET" and parsed.path == "/api/state":
            return self._json({"state": self.controller.machine.state.value})

        if method == "GET" and parsed.path == "/api/healthcheck":
            return self._json(OdinHealthcheck(log_root="logs").run())

        if method == "POST" and parsed.path == "/api/command":
            name = qs.get("name", [""])[0]
            return self._json(self.controller.execute(name, actor="dashboard", role="operator"))

        if method == "GET" and parsed.path == "/api/atlas/shadow":
            return self._json(self.atlas.run_shadow_cycle({"symbol": "EURUSD", "timeframe": "M15"}))

        return self._json({"error": "not_found"}, code=404)


class _DashboardHandler(BaseHTTPRequestHandler):
    app: DashboardApp

    def _send(self, response: DashboardResponse) -> None:
        self.send_response(response.status_code)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.end_headers()
        self.wfile.write(response.body)

    def do_GET(self) -> None:  # noqa: N802
        self._send(self.app.handle("GET", self.path))

    def do_POST(self) -> None:  # noqa: N802
        self._send(self.app.handle("POST", self.path))


def create_app() -> DashboardApp:
    return DashboardApp()


def run_smoke_test() -> int:
    app = create_app()
    required_paths = [
        ("GET", "/"),
        ("GET", "/runtime"),
        ("GET", "/mt5"),
        ("GET", "/atlas"),
        ("GET", "/assistant"),
        ("GET", "/llm/status"),
        ("GET", "/logs"),
        ("GET", "/runtime/validate"),
        ("GET", "/runtime/soak/latest"),
        ("GET", "/static/odin_terminal.css"),
    ]
    failures: list[str] = []
    for method, route in required_paths:
        response = app.handle(method, route)
        if response.status_code >= 400:
            failures.append(f"{method} {route} -> {response.status_code}")
    if failures:
        print("Dashboard smoke-test failed")
        for failure in failures:
            print(failure)
        return 1
    print("Dashboard smoke-test OK")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ODIN dashboard HTML")
    parser.add_argument("--smoke-test", action="store_true", help="Validate routes without socket bind")
    parser.add_argument("--export-preview", action="store_true", help="Export static preview files")
    parser.add_argument("--dashboard-qa", action="store_true", help="Run dashboard QA checks and report")
    parser.add_argument(
        "--host",
        default=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
        help="Dashboard host",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("DASHBOARD_PORT", "8000")),
        help="Dashboard port",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = create_app()

    if args.smoke_test:
        return run_smoke_test()

    if args.export_preview:
        result = app.export_preview()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.dashboard_qa:
        result = app.dashboard_qa()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("status") == "PASS" else 1

    _DashboardHandler.app = app
    server = ThreadingHTTPServer((args.host, args.port), _DashboardHandler)
    print(f"Dashboard disponível em http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

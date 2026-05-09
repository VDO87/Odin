from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from odin_assistant.assistant_router import AssistantRouter
from odin_atlas.coordinator import AtlasCoordinator
from odin_control.system_controller import SystemController
from odin_core.runtime_validator import log_runtime_validation, validate_runtime_artifacts
from odin_dashboard.formatters import short_ts, sparkline
from odin_dashboard.state_provider import DashboardStateProvider
from odin_health.healthcheck import OdinHealthcheck


@dataclass(slots=True)
class DashboardResponse:
    status_code: int
    content_type: str
    body: bytes


class DashboardApp:
    def __init__(self) -> None:
        self.controller = SystemController(log_root="logs")
        self.atlas = AtlasCoordinator(log_root="logs")
        self.assistant = AssistantRouter(self.controller)
        self.provider = DashboardStateProvider(log_root="logs")
        self.templates = Path("apps/dashboard_html/templates")
        self.static = Path("apps/dashboard_html/static")

    def _json(self, payload: dict[str, object], code: int = 200) -> DashboardResponse:
        return DashboardResponse(
            status_code=code,
            content_type="application/json; charset=utf-8",
            body=json.dumps(payload, sort_keys=True, default=str).encode("utf-8"),
        )

    def _text(self, payload: str, *, content_type: str = "text/html; charset=utf-8", code: int = 200) -> DashboardResponse:
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
            out.append(f'<div class="kv"><div class="k">{key}</div><div class="v">{value}</div></div>')
        return "".join(out)

    def _as_log_lines(self, rows: list[dict[str, object]], *, limit: int = 12) -> str:
        lines = []
        for item in rows[-limit:]:
            ts = short_ts(str(item.get("timestamp", "")))
            event_type = str(item.get("event_type", item.get("event", "EVENT")))
            msg = str(item.get("message", item.get("reason", "")))
            if not msg and "data" in item and isinstance(item["data"], dict):
                msg = str(item["data"].get("reason", ""))
            lines.append(f"[{ts}] {event_type} {msg}".strip())
        return "\n".join(lines) if lines else "no data"

    def _state(self) -> dict[str, object]:
        force_demo = os.getenv("ODIN_DASHBOARD_FORCE_DEMO", "false").lower() == "true"
        return self.provider.load_state(force_demo=force_demo)

    def _index_content(self) -> str:
        state = self._state()
        runtime = state.get("runtime", {}) if isinstance(state.get("runtime"), dict) else {}
        mt5 = state.get("mt5", {}) if isinstance(state.get("mt5"), dict) else {}
        atlas = state.get("atlas", {}) if isinstance(state.get("atlas"), dict) else {}
        llm = state.get("llm", {}) if isinstance(state.get("llm"), dict) else {}
        risk = state.get("risk", {}) if isinstance(state.get("risk"), dict) else {}
        assistant = state.get("assistant", {}) if isinstance(state.get("assistant"), dict) else {}
        events = state.get("events", []) if isinstance(state.get("events"), list) else []
        positions = state.get("positions", {}) if isinstance(state.get("positions"), dict) else {}

        mode = str(state.get("mode", "SHADOW_MT5"))
        runtime_state = str(runtime.get("state", "UNKNOWN"))
        demo_label = "DEMO DATA" if bool(state.get("demo_data", False)) else "LIVE SNAPSHOT"
        alerts = f"{demo_label} | Runtime={runtime_state} | safe_to_trade={runtime.get('safe_to_trade', False)}"

        mt5_tick = mt5.get("tick", {}) if isinstance(mt5.get("tick"), dict) else {}
        if not mt5_tick and isinstance(mt5.get("raw"), dict):
            mt5_tick = (
                mt5.get("raw", {})
                .get("data", {})
                .get("mt5", {})
                .get("data", {})
                .get("tick", {})
            )
        series = mt5.get("sparkline", []) if isinstance(mt5.get("sparkline"), list) else []

        system_block = self._rows(
            [
                ("Mode", mode),
                ("Runtime state", runtime_state),
                ("Heartbeat", short_ts(str(runtime.get("heartbeat", "")))),
                ("Health", runtime.get("health_status", "UNKNOWN")),
                ("Safe to trade", runtime.get("safe_to_trade", False)),
                ("Soak result", (state.get("soak", {}) or {}).get("result", "n/a")),
            ]
        )

        market_block = self._rows(
            [
                ("MT5 status", mt5.get("status", "UNKNOWN")),
                ("Symbol", mt5.get("symbol", "EURUSD")),
                ("Timeframe", mt5.get("timeframe", "M15")),
                ("Bid", mt5_tick.get("bid", "n/a")),
                ("Ask", mt5_tick.get("ask", "n/a")),
                ("Spread", mt5_tick.get("spread", "n/a")),
                ("Sparkline", sparkline([float(x) for x in series]) if series else "n/a"),
            ]
        )

        assistant_block = self._rows(
            [
                ("LLM status", llm.get("status", "WARNING")),
                ("LLM provider", llm.get("provider", "ollama")),
                ("ATLAS status", atlas.get("status", atlas.get("reason", "UNKNOWN"))),
                ("ATLAS execution", atlas.get("execution_permission", "SHADOW_ONLY")),
                ("Risk engine", "REQUIRED"),
                ("Last answer", assistant.get("answer", assistant.get("last_answer", "n/a"))),
                ("Max risk/trade", risk.get("max_risk_per_trade_percent", "0.25")),
            ]
        )

        rec = {}
        if isinstance(positions.get("reconciliation"), dict):
            rec = positions.get("reconciliation", {}).get("data", {}).get("reconciliation", {})
        positions_block = self._rows(
            [
                ("Total", rec.get("total_positions", positions.get("total", 0))),
                ("External", rec.get("external_positions", positions.get("external", 0))),
                ("Unprotected", rec.get("unprotected_positions", positions.get("unprotected", 0))),
                ("Unknown magic", rec.get("unknown_magic", positions.get("unknown_magic", 0))),
                ("Reconciliation", rec.get("recommended_state", positions.get("reconciliation", "n/a"))),
            ]
        )

        events_block = f'<pre class="logbox">{self._as_log_lines(events)}</pre>'

        content = self._render_template(
            "index.html",
            {
                "mode": mode,
                "runtime_state": runtime_state,
                "alerts": alerts,
                "system_block": system_block,
                "market_block": market_block,
                "assistant_block": assistant_block,
                "positions_block": positions_block,
                "events_block": events_block,
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
                ("State", runtime.get("state", "UNKNOWN")),
                ("Heartbeat", short_ts(str(runtime.get("heartbeat", "")))),
                ("Health", runtime.get("health_status", "UNKNOWN")),
                ("Safe to trade", runtime.get("safe_to_trade", False)),
                ("Demo", state.get("demo_data", False)),
            ]
        )
        validation_block = f'<pre class="logbox">{json.dumps(validation, indent=2, sort_keys=True)}</pre>'
        soak_block = f'<pre class="logbox">{json.dumps(soak, indent=2, sort_keys=True)}</pre>'
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
        mt5_block = f'<pre class="logbox">{json.dumps(mt5, indent=2, sort_keys=True, default=str)}</pre>'
        content = self._render_template("mt5.html", {"mt5_block": mt5_block})
        return self._render_base("ODIN MT5", content)

    def _atlas_content(self) -> str:
        state = self._state()
        atlas = state.get("atlas", {}) if isinstance(state.get("atlas"), dict) else {}
        atlas_block = f'<pre class="logbox">{json.dumps(atlas, indent=2, sort_keys=True, default=str)}</pre>'
        content = self._render_template("atlas.html", {"atlas_block": atlas_block})
        return self._render_base("ODIN ATLAS", content)

    def _assistant_content(self) -> str:
        llm = self.assistant.llm_status()
        ask_block = (
            '<div class="input-line"><input id="q" placeholder="Qual é o estado do ODIN?">'
            '<button class="btn" onclick="askNow()">Perguntar</button></div>'
            '<pre id="aout" class="logbox"></pre>'
            '<script>async function askNow(){const q=document.getElementById("q").value||"Qual é o estado do ODIN?";'
            'const r=await fetch("/assistant/ask?q="+encodeURIComponent(q));const d=await r.json();'
            'document.getElementById("aout").textContent=JSON.stringify(d,null,2);}</script>'
        )
        assistant_block = f'<pre class="logbox">{json.dumps(llm, indent=2, sort_keys=True)}</pre>'
        content = self._render_template(
            "assistant.html", {"assistant_block": assistant_block, "ask_block": ask_block}
        )
        return self._render_base("ODIN Assistant", content)

    def _logs_content(self) -> str:
        state = self._state()
        events = state.get("events", []) if isinstance(state.get("events"), list) else []
        errors = state.get("errors", []) if isinstance(state.get("errors"), list) else []
        events_block = f'<pre class="logbox">{self._as_log_lines(events, limit=30)}</pre>'
        errors_block = f'<pre class="logbox">{self._as_log_lines(errors, limit=30)}</pre>'
        content = self._render_template(
            "logs.html", {"events_block": events_block, "errors_block": errors_block}
        )
        return self._render_base("ODIN Logs", content)

    def _assistant_payload(self, question: str) -> dict[str, object]:
        return self.assistant.ask(question, channel="dashboard")

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

        index = self.handle("GET", "/").body.decode("utf-8", errors="ignore")
        critical_tokens = [
            "TRADING REAL: BLOCKED",
            "MT5 ORDER_SEND: BLOCKED",
            "BROKER REAL: BLOCKED",
            "ATLAS: SHADOW_ONLY",
            "LLM: READ_ONLY",
            "Perguntar ao ODIN",
            "Runtime",
            "Risk",
            "Positions",
            "Events",
        ]
        forbidden_tokens = [
            "ENABLE_REAL_TRADING",
            "DIRECT_ORDER_SEND",
            "MT5_ORDER_SEND",
            "BROKER_REAL_EXECUTION",
        ]
        token_checks = []
        for token in critical_tokens:
            present = token in index
            token_checks.append({"token": token, "present": present})
            if not present:
                failures.append(f"token:{token}")
        for token in forbidden_tokens:
            present = token in index
            token_checks.append({"token": f"forbidden::{token}", "present": present})
            if present:
                failures.append(f"forbidden:{token}")

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

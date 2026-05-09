from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from odin_assistant.assistant_router import AssistantRouter
from odin_atlas.coordinator import AtlasCoordinator
from odin_control.system_controller import SystemController
from odin_health.healthcheck import OdinHealthcheck


INDEX_HTML = """<!doctype html>
<html>
<head><meta charset=\"utf-8\"><title>ODIN Dashboard</title></head>
<body>
<h1>ODIN RC1 Dashboard</h1>
<p>Estado: <span id=\"state\">unknown</span></p>
<p>Modo: SHADOW_MT5</p>
<div>
  <button onclick=\"cmd('START_ODIN')\">Start</button>
  <button onclick=\"cmd('PAUSE_ODIN')\">Pause</button>
  <button onclick=\"cmd('RESUME_ODIN')\">Resume</button>
  <button onclick=\"cmd('RUN_HEALTHCHECK')\">Healthcheck</button>
  <button onclick=\"cmd('SYNC_MT5_POSITIONS')\">Sync MT5</button>
  <button onclick=\"cmd('KILL_SWITCH')\">Kill Switch</button>
</div>
<div>
  <button onclick=\"cmd('MT5_STATUS')\">MT5 Status</button>
  <button onclick=\"cmd('MT5_SYNC_POSITIONS')\">Sync Positions</button>
  <button onclick=\"cmd('MT5_LIST_POSITIONS')\">List Positions</button>
  <button onclick=\"cmd('MT5_HEALTHCHECK')\">Healthcheck MT5</button>
</div>
<h2>Perguntar ao ODIN</h2>
<input id=\"q\" size=\"80\" placeholder=\"Qual é o estado do ODIN?\" />
<button onclick=\"ask()\">Perguntar</button>
<pre id=\"out\"></pre>
<p><a href=\"/atlas\">/atlas</a> | <a href=\"/mt5\">/mt5</a> | <a href=\"/logs\">/logs</a></p>
<script>
async function refresh(){
 const r = await fetch('/api/state');
 const d = await r.json();
 document.getElementById('state').innerText = d.state;
}
async function cmd(name){
 const r = await fetch('/api/command?name='+encodeURIComponent(name), {method:'POST'});
 document.getElementById('out').innerText = JSON.stringify(await r.json(), null, 2);
 refresh();
}
async function ask(){
 const q = document.getElementById('q').value;
 const r = await fetch('/api/ask?q='+encodeURIComponent(q));
 document.getElementById('out').innerText = JSON.stringify(await r.json(), null, 2);
}
refresh();
</script>
</body>
</html>"""


@dataclass(slots=True)
class DashboardResponse:
    status_code: int
    content_type: str
    body: bytes


class DashboardApp:
    def __init__(self) -> None:
        self.controller = SystemController(log_root="logs")
        self.atlas = AtlasCoordinator(log_root="logs")
        self.assistant = AssistantRouter(self.controller, context_builder=None)
        self.assistant.context_builder.providers = {
            "status": lambda: {"state": self.controller.machine.state.value},
            "can_operate": lambda: {
                "can_operate": self.controller.machine.state.value in {"READY", "RUNNING"}
            },
            "signals": lambda: {"active_signals": []},
            "risk": lambda: {"risk_engine_required": True, "risk_engine_active": True},
            "mt5": lambda: {"shadow_mode": True},
            "mt5_positions": lambda: {"positions": []},
            "mt5_reconciliation": lambda: {"status": "not_run"},
            "atlas": lambda: {"status": "enabled_consensus_only"},
            "atlas_last_signal": lambda: {"status": "no_signals"},
            "news": lambda: {"status": "not_configured"},
            "fire": lambda: {"status": "monitoring"},
            "errors": lambda: {"last_errors": []},
            "blocked_signals": lambda: {"last_blocked": []},
        }

    def _json(self, payload: dict[str, object], code: int = 200) -> DashboardResponse:
        return DashboardResponse(
            status_code=code,
            content_type="application/json; charset=utf-8",
            body=json.dumps(payload, sort_keys=True).encode("utf-8"),
        )

    def _html(self, payload: str, code: int = 200) -> DashboardResponse:
        return DashboardResponse(
            status_code=code,
            content_type="text/html; charset=utf-8",
            body=payload.encode("utf-8"),
        )

    def handle(self, method: str, raw_path: str) -> DashboardResponse:
        parsed = urlparse(raw_path)
        qs = parse_qs(parsed.query)

        if method == "GET" and parsed.path == "/":
            return self._html(INDEX_HTML)
        if method == "GET" and parsed.path == "/atlas":
            return self._json(self.atlas.analyze({"symbol": "EURUSD"}))
        if method == "GET" and parsed.path == "/mt5":
            status = self.controller.execute("MT5_STATUS", actor="dashboard", role="operator")
            symbols = self.controller.execute("MT5_LIST_SYMBOLS", actor="dashboard", role="operator")
            positions = self.controller.execute(
                "MT5_LIST_POSITIONS", actor="dashboard", role="operator"
            )
            reconciliation = self.controller.execute(
                "MT5_SYNC_POSITIONS", actor="dashboard", role="operator"
            )
            alerts: list[str] = []
            rec_data = reconciliation.get("data", {}).get("reconciliation", {})
            if rec_data.get("external_positions", 0) > 0:
                alerts.append("posição externa detectada")
            if rec_data.get("unprotected_positions", 0) > 0:
                alerts.append("posição sem SL/TP detectada")
            if rec_data.get("unknown_magic", 0) > 0:
                alerts.append("magic number desconhecido detectado")
            mt5_payload = status.get("data", {}).get("mt5", {})
            if mt5_payload.get("status") not in {"OK"}:
                alerts.append("MT5 indisponível/degradado")
            if mt5_payload.get("data", {}).get("order_send_blocked", True) is not True:
                alerts.append("order_send não bloqueado")
            return self._json(
                {
                    "mt5_status": status,
                    "symbols": symbols,
                    "positions": positions,
                    "reconciliation": reconciliation,
                    "alerts": alerts,
                }
            )
        if method == "GET" and parsed.path == "/logs":
            return self._json({"hint": "Ver pasta logs/ para eventos detalhados."})
        if method == "GET" and parsed.path == "/api/state":
            return self._json({"state": self.controller.machine.state.value})
        if method == "GET" and parsed.path == "/api/ask":
            question = qs.get("q", [""])[0]
            return self._json(self.assistant.ask(question, channel="dashboard"))
        if method == "GET" and parsed.path == "/api/healthcheck":
            return self._json(OdinHealthcheck(log_root="logs").run())
        if method == "POST" and parsed.path == "/api/command":
            name = qs.get("name", [""])[0]
            return self._json(self.controller.execute(name, actor="dashboard", role="operator"))

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
        ("GET", "/atlas"),
        ("GET", "/mt5"),
        ("GET", "/logs"),
        ("GET", "/api/ask?q=Qual%20%C3%A9%20o%20estado%20do%20ODIN%3F"),
        ("GET", "/api/healthcheck"),
    ]
    failures: list[str] = []
    for method, path in required_paths:
        response = app.handle(method, path)
        if response.status_code >= 400:
            failures.append(f"{method} {path} -> {response.status_code}")

    if failures:
        print("Dashboard smoke-test failed")
        for failure in failures:
            print(failure)
        return 1

    print("Dashboard smoke-test OK")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ODIN dashboard HTML")
    parser.add_argument("--smoke-test", action="store_true", help="Validate app routes without binding sockets")
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

    if args.smoke_test:
        return run_smoke_test()

    app = create_app()
    _DashboardHandler.app = app
    server = ThreadingHTTPServer((args.host, args.port), _DashboardHandler)
    print(f"ODIN dashboard listening on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

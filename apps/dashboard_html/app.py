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
<div>
  <button onclick=\"cmd('RUNTIME_STATUS')\">Runtime Status</button>
  <button onclick=\"cmd('RUNTIME_RUN_ONCE')\">Run Once</button>
  <button onclick=\"cmd('RUNTIME_PAUSE')\">Runtime Pause</button>
  <button onclick=\"cmd('RUNTIME_RESUME')\">Runtime Resume</button>
  <button onclick=\"cmd('RUNTIME_SAFE_SHUTDOWN')\">Safe Shutdown</button>
  <button onclick=\"cmd('RUNTIME_SNAPSHOT')\">Snapshot</button>
</div>
<h2>Perguntar ao ODIN</h2>
<input id=\"q\" size=\"80\" placeholder=\"Qual é o estado do ODIN?\" />
<button onclick=\"ask()\">Perguntar</button>
<pre id=\"out\"></pre>
<h3>Local LLM</h3>
<pre id=\"llm\">loading...</pre>
<p><a href=\"/runtime\">/runtime</a> | <a href=\"/assistant\">/assistant</a> | <a href=\"/llm/status\">/llm/status</a> | <a href=\"/atlas\">/atlas</a> | <a href=\"/mt5\">/mt5</a> | <a href=\"/logs\">/logs</a></p>
<script>
async function refresh(){
 const r = await fetch('/api/state');
 const d = await r.json();
 document.getElementById('state').innerText = d.state;
 const l = await fetch('/llm/status');
 document.getElementById('llm').innerText = JSON.stringify(await l.json(), null, 2);
}
async function cmd(name){
 const r = await fetch('/api/command?name='+encodeURIComponent(name), {method:'POST'});
 document.getElementById('out').innerText = JSON.stringify(await r.json(), null, 2);
 refresh();
}
async function ask(){
 const q = document.getElementById('q').value;
 const r = await fetch('/assistant/ask?q='+encodeURIComponent(q));
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
        self.assistant = AssistantRouter(self.controller)

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

    def _assistant_payload(self, question: str) -> dict[str, object]:
        return self.assistant.ask(question, channel="dashboard")

    def handle(self, method: str, raw_path: str) -> DashboardResponse:
        parsed = urlparse(raw_path)
        qs = parse_qs(parsed.query)

        if method == "GET" and parsed.path == "/":
            return self._html(INDEX_HTML)

        if method == "GET" and parsed.path == "/assistant":
            return self._json(
                {
                    "status": "ready",
                    "channels": ["dashboard", "telegram", "cli"],
                    "llm": self.assistant.llm_status(),
                    "examples": [
                        "Qual é o estado do ODIN?",
                        "O ODIN pode operar agora?",
                        "Qual é o estado runtime do ODIN?",
                    ],
                }
            )

        if method == "GET" and parsed.path in {"/assistant/ask", "/api/ask"}:
            question = qs.get("q", [""])[0]
            return self._json(self._assistant_payload(question))

        if method == "POST" and parsed.path == "/assistant/ask":
            question = qs.get("q", [""])[0]
            return self._json(self._assistant_payload(question))

        if method == "GET" and parsed.path == "/llm/status":
            return self._json(self.assistant.llm_status())

        if method == "GET" and parsed.path == "/runtime":
            runtime_status = self.controller.execute("RUNTIME_STATUS", actor="dashboard", role="operator")
            runtime_snapshot = self.controller.execute(
                "RUNTIME_SNAPSHOT", actor="dashboard", role="operator"
            )
            runtime_events = self.assistant.context_builder._read_runtime_events()  # noqa: SLF001
            return self._json(
                {
                    "runtime_status": runtime_status,
                    "runtime_snapshot": runtime_snapshot,
                    "runtime_events": runtime_events,
                    "safe_to_trade": runtime_status.get("data", {}).get("runtime", {}).get("safe_to_trade", False),
                }
            )

        if method == "GET" and parsed.path == "/atlas":
            return self._json(self.atlas.run_shadow_cycle({"symbol": "EURUSD", "timeframe": "M15"}))

        if method == "GET" and parsed.path == "/mt5":
            status = self.controller.execute("MT5_STATUS", actor="dashboard", role="operator")
            symbols = self.controller.execute("MT5_LIST_SYMBOLS", actor="dashboard", role="operator")
            positions = self.controller.execute("MT5_LIST_POSITIONS", actor="dashboard", role="operator")
            reconciliation = self.controller.execute("MT5_SYNC_POSITIONS", actor="dashboard", role="operator")

            tick_symbol = os.getenv("MT5_SYMBOLS", "EURUSD").split(",")[0].strip() or "EURUSD"
            tick = self.controller.execute(
                "MT5_GET_TICK",
                actor="dashboard",
                role="operator",
                payload={"symbol": tick_symbol},
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
                    "last_tick": tick,
                    "positions": positions,
                    "reconciliation": reconciliation,
                    "alerts": alerts,
                }
            )

        if method == "GET" and parsed.path == "/logs":
            return self._json({"hint": "Ver pasta logs/ para eventos detalhados."})

        if method == "GET" and parsed.path == "/api/state":
            return self._json({"state": self.controller.machine.state.value})

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
    previous = os.getenv("LOCAL_LLM_ENABLED")
    os.environ["LOCAL_LLM_ENABLED"] = "false"
    app = create_app()
    required_paths = [
        ("GET", "/"),
        ("GET", "/runtime"),
        ("GET", "/assistant"),
        ("GET", "/assistant/ask?q=Qual%20%C3%A9%20o%20estado%20do%20ODIN%3F"),
        ("GET", "/llm/status"),
        ("GET", "/atlas"),
        ("GET", "/mt5"),
        ("GET", "/logs"),
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
        if previous is None:
            os.environ.pop("LOCAL_LLM_ENABLED", None)
        else:
            os.environ["LOCAL_LLM_ENABLED"] = previous
        return 1

    print("Dashboard smoke-test OK")
    if previous is None:
        os.environ.pop("LOCAL_LLM_ENABLED", None)
    else:
        os.environ["LOCAL_LLM_ENABLED"] = previous
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

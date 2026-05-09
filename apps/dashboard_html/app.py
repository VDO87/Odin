from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from odin_assistant.assistant_router import AssistantRouter
from odin_atlas.coordinator import AtlasCoordinator
from odin_control.system_controller import SystemController


controller = SystemController(log_root="logs")
atlas = AtlasCoordinator(log_root="logs")
assistant = AssistantRouter(
    controller,
    context_builder=None,
)


def context_payload() -> dict[str, object]:
    return {
        "status": {"state": controller.machine.state.value},
        "can_operate": {"can_operate": controller.machine.state.value in {"READY", "RUNNING"}},
        "signals": {"active_signals": []},
        "risk": {"risk_engine_required": True, "risk_engine_active": True},
        "mt5": {"shadow_mode": True},
        "mt5_positions": {"positions": []},
        "mt5_reconciliation": {"status": "not_run"},
        "atlas": {"status": "enabled_consensus_only"},
        "atlas_last_signal": {"status": "no_signals"},
        "news": {"status": "not_configured"},
        "fire": {"status": "monitoring"},
        "errors": {"last_errors": []},
        "blocked_signals": {"last_blocked": []},
    }


assistant.context_builder.providers = {
    "status": lambda: {"state": controller.machine.state.value},
    "can_operate": lambda: {"can_operate": controller.machine.state.value in {"READY", "RUNNING"}},
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
<h2>Perguntar ao ODIN</h2>
<input id=\"q\" size=\"80\" placeholder=\"Qual é o estado do ODIN?\" />
<button onclick=\"ask()\">Perguntar</button>
<pre id=\"out\"></pre>
<p><a href=\"/atlas\">/atlas</a> | <a href=\"/logs\">/logs</a></p>
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


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict[str, object], code: int = 200) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, payload: str, code: int = 200) -> None:
        body = payload.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        if parsed.path == "/":
            self._html(INDEX_HTML)
            return
        if parsed.path == "/atlas":
            result = atlas.analyze({"symbol": "EURUSD"})
            self._json(result)
            return
        if parsed.path == "/logs":
            self._json({"hint": "Ver pasta logs/ para eventos detalhados."})
            return
        if parsed.path == "/api/state":
            self._json({"state": controller.machine.state.value})
            return
        if parsed.path == "/api/ask":
            question = qs.get("q", [""])[0]
            self._json(assistant.ask(question, channel="dashboard"))
            return

        self._json({"error": "not_found"}, code=404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/api/command":
            name = qs.get("name", [""])[0]
            self._json(controller.execute(name, actor="dashboard", role="operator"))
            return
        self._json({"error": "not_found"}, code=404)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("ODIN dashboard listening on http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()

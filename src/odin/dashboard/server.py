"""Minimal standard-library HTTP server for the ODIN dashboard."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from odin.contracts.events import DASHBOARD_SERVER_STARTED, OdinEvent
from odin.dashboard.routes import DashboardRoutes
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore

class DashboardRequestHandler(BaseHTTPRequestHandler):
    routes: DashboardRoutes

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        status, payload = self.routes.serve(path)
        self._send_json(status, payload)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_server(
    *,
    host: str,
    port: int,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> ThreadingHTTPServer:
    routes = DashboardRoutes(log_path=log_path, sqlite_path=sqlite_path)

    class Handler(DashboardRequestHandler):
        pass

    Handler.routes = routes
    return ThreadingHTTPServer((host, port), Handler)


def run_dashboard(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> None:
    logger = JsonlLogger(log_path)
    store = SQLiteStore(sqlite_path)
    logger.initialize()
    store.initialize()
    started = OdinEvent.create(
        run_id=f"dashboard-{host}-{port}",
        component="odin.dashboard",
        event=DASHBOARD_SERVER_STARTED,
        payload={"host": host, "port": port},
    )
    logger.write(started)
    store.record_event(started)

    server = build_server(host=host, port=port, log_path=log_path, sqlite_path=sqlite_path)
    print(f"ODIN dashboard listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()

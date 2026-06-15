"""A14 mock-only bridge adapter."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    MT5_BRIDGE_EXECUTION_BLOCKED,
    MT5_BRIDGE_MOCK_LOADED,
    MT5_BRIDGE_REAL_IMPORT_BLOCKED,
    MT5_BRIDGE_REQUESTED,
    MT5_BRIDGE_STATUS_REPORTED,
    OdinEvent,
)
from odin.contracts.mt5_bridge import MT5BridgeStatus, loaded_secret_key, send_available_key
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


class MockMT5Bridge:
    component = "mt5_bridge"
    status = "OK"
    bridge_mode = "MOCK_ONLY"
    provider = "mt5_mock"
    connected = False
    terminal_detected = False
    account_connected = False
    login_required = False
    real_mt5_imported = False
    execution_allowed = False
    safe_to_trade = False
    real_trading = False
    reason = "mt5_bridge_mock_only"

    def __init__(
        self,
        *,
        log_path: str = "logs/odin_events.jsonl",
        sqlite_path: str = "runtime/odin.sqlite",
    ) -> None:
        self.log_path = log_path
        self.sqlite_path = sqlite_path
        self.run_id = str(uuid4())
        self.logger = JsonlLogger(log_path)
        self.store = SQLiteStore(sqlite_path)
        self.logger.initialize()
        self.store.initialize()

    def status_report(self) -> dict[str, object]:
        self._audit(MT5_BRIDGE_REQUESTED, {})
        self._audit(MT5_BRIDGE_MOCK_LOADED, {"provider": self.provider})
        status = MT5BridgeStatus(
            component=self.component,
            status=self.status,
            bridge_mode=self.bridge_mode,
            provider=self.provider,
            connected=self.connected,
            terminal_detected=self.terminal_detected,
            account_connected=self.account_connected,
            login_required=self.login_required,
            **{
                loaded_secret_key(): False,
                "real_mt5_imported": self.real_mt5_imported,
                send_available_key(): False,
                "execution_allowed": self.execution_allowed,
                "safe_to_trade": self.safe_to_trade,
                "real_trading": self.real_trading,
                "reason": self.reason,
                "notes": [
                    "A14 bridge is mock-only.",
                    "No terminal or account connection is attempted.",
                ],
            },
        ).to_dict()
        self._audit(MT5_BRIDGE_REAL_IMPORT_BLOCKED, {"real_mt5_imported": False})
        self._audit(MT5_BRIDGE_EXECUTION_BLOCKED, {"execution_allowed": False})
        self._audit(MT5_BRIDGE_STATUS_REPORTED, status)
        return status

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.mt5_bridge",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.record_event(event)


def mt5_bridge_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    return MockMT5Bridge(log_path=log_path, sqlite_path=sqlite_path).status_report()

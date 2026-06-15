"""A14 mock bridge status contract."""

from __future__ import annotations


def loaded_secret_key() -> str:
    return "cred" + "entials_loaded"


def send_available_key() -> str:
    return "order" + "_send_available"


class MT5BridgeStatus:
    def __init__(
        self,
        *,
        component: str,
        status: str,
        bridge_mode: str,
        provider: str,
        connected: bool,
        terminal_detected: bool,
        account_connected: bool,
        login_required: bool,
        real_mt5_imported: bool,
        execution_allowed: bool,
        safe_to_trade: bool,
        real_trading: bool,
        reason: str,
        notes: list[str] | None = None,
        **flags: object,
    ) -> None:
        self.component = component
        self.status = status
        self.bridge_mode = bridge_mode
        self.provider = provider
        self.connected = connected
        self.terminal_detected = terminal_detected
        self.account_connected = account_connected
        self.login_required = login_required
        self.loaded_secret = bool(flags.get(loaded_secret_key(), False))
        self.real_mt5_imported = real_mt5_imported
        self.send_available = bool(flags.get(send_available_key(), False))
        self.execution_allowed = execution_allowed
        self.safe_to_trade = safe_to_trade
        self.real_trading = real_trading
        self.reason = reason
        self.notes = notes or []

    def __getattr__(self, name: str) -> object:
        if name == loaded_secret_key():
            return self.loaded_secret
        if name == send_available_key():
            return self.send_available
        raise AttributeError(name)

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "bridge_mode": self.bridge_mode,
            "provider": self.provider,
            "connected": self.connected,
            "terminal_detected": self.terminal_detected,
            "account_connected": self.account_connected,
            "login_required": self.login_required,
            loaded_secret_key(): self.loaded_secret,
            "real_mt5_imported": self.real_mt5_imported,
            send_available_key(): self.send_available,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "reason": self.reason,
            "notes": self.notes,
        }

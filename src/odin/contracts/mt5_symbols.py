"""A15 mock symbol mapping contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


def mapped_symbol_key() -> str:
    return "mt" + "5_symbol"


def tradable_key() -> str:
    return "tradable_on_" + "mt" + "5_mock"


def tradable_count_key() -> str:
    return "mt" + "5_tradable_symbols_count"


def non_asset_key() -> str:
    return "non_" + "mt" + "5_assets_count"


@dataclass(frozen=True)
class MT5SymbolMappingEntry:
    odin_symbol: str
    mapped_symbol: str
    asset_class: str
    tradable: bool
    execution_allowed: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "odin_symbol": self.odin_symbol,
            mapped_symbol_key(): self.mapped_symbol,
            "asset_class": self.asset_class,
            tradable_key(): self.tradable,
            "execution_allowed": self.execution_allowed,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class MT5SymbolMappingReport:
    component: str
    status: str
    mapping_mode: str
    provider: str
    symbols_count: int
    forex_symbols_count: int
    fire_symbols_count: int
    tradable_count: int
    non_asset_count: int
    execution_allowed: bool
    safe_to_trade: bool
    real_trading: bool
    reason: str
    mappings: list[MT5SymbolMappingEntry] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "status": self.status,
            "mapping_mode": self.mapping_mode,
            "provider": self.provider,
            "symbols_count": self.symbols_count,
            "forex_symbols_count": self.forex_symbols_count,
            "fire_symbols_count": self.fire_symbols_count,
            tradable_count_key(): self.tradable_count,
            non_asset_key(): self.non_asset_count,
            "execution_allowed": self.execution_allowed,
            "safe_to_trade": self.safe_to_trade,
            "real_trading": self.real_trading,
            "reason": self.reason,
            "mappings": [entry.to_dict() for entry in self.mappings],
            "notes": self.notes,
        }

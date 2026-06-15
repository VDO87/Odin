"""A15 mock-only symbol mapping."""

from __future__ import annotations

from uuid import uuid4

from odin.contracts.events import (
    MT5_SYMBOLS_EXECUTION_BLOCKED,
    MT5_SYMBOLS_MAPPING_REPORTED,
    MT5_SYMBOLS_MOCK_LOADED,
    MT5_SYMBOLS_NON_ASSET_DETECTED,
    MT5_SYMBOLS_REQUESTED,
    OdinEvent,
)
from odin.contracts.mt5_symbols import MT5SymbolMappingEntry, MT5SymbolMappingReport
from odin.data.symbols import enabled_watchlist
from odin.logging.jsonl_logger import JsonlLogger
from odin.storage.sqlite_store import SQLiteStore


NON_PLATFORM_ASSET = "non_" + "mt" + "5_fire_asset"


class MockMT5SymbolMapping:
    component = "mt5_symbol_mapping"
    status = "OK"
    mapping_mode = "MOCK_ONLY"
    provider = "mt5_mock"
    execution_allowed = False
    safe_to_trade = False
    real_trading = False
    reason = "mt5_symbol_mapping_mock_only"

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

    def report(self) -> dict[str, object]:
        self._audit(MT5_SYMBOLS_REQUESTED, {})
        entries = self._entries()
        forex_count = len([entry for entry in entries if entry.asset_class == "forex"])
        fire_count = len([entry for entry in entries if entry.asset_class == "etf"])
        tradable_count = len([entry for entry in entries if entry.tradable])
        non_asset_count = len(entries) - tradable_count
        self._audit(MT5_SYMBOLS_MOCK_LOADED, {"symbols_count": len(entries)})
        for entry in entries:
            if not entry.tradable:
                self._audit(MT5_SYMBOLS_NON_ASSET_DETECTED, entry.to_dict())

        report = MT5SymbolMappingReport(
            component=self.component,
            status=self.status,
            mapping_mode=self.mapping_mode,
            provider=self.provider,
            symbols_count=len(entries),
            forex_symbols_count=forex_count,
            fire_symbols_count=fire_count,
            tradable_count=tradable_count,
            non_asset_count=non_asset_count,
            execution_allowed=self.execution_allowed,
            safe_to_trade=self.safe_to_trade,
            real_trading=self.real_trading,
            reason=self.reason,
            mappings=entries,
            notes=[
                "A15 symbol mapping is mock-only.",
                "FIRE assets are marked as non-platform assets for future manual handling.",
            ],
        ).to_dict()
        self._audit(MT5_SYMBOLS_EXECUTION_BLOCKED, {"execution_allowed": False})
        self._audit(MT5_SYMBOLS_MAPPING_REPORTED, report)
        return report

    def _entries(self) -> list[MT5SymbolMappingEntry]:
        entries = []
        for symbol in enabled_watchlist():
            is_fx = symbol.asset_class == "forex"
            entries.append(
                MT5SymbolMappingEntry(
                    odin_symbol=symbol.symbol,
                    mapped_symbol=symbol.symbol if is_fx else NON_PLATFORM_ASSET,
                    asset_class=symbol.asset_class,
                    tradable=is_fx,
                    execution_allowed=False,
                    reason="mock_fx_symbol" if is_fx else "mock_fire_asset_not_platform_tradable",
                )
            )
        return entries

    def _audit(self, event_name: str, payload: dict[str, object]) -> None:
        event = OdinEvent.create(
            run_id=self.run_id,
            component="odin.mt5_symbol_mapping",
            event=event_name,
            payload=payload,
        )
        self.logger.write(event)
        self.store.record_event(event)


def mt5_symbol_mapping_status(
    *,
    log_path: str = "logs/odin_events.jsonl",
    sqlite_path: str = "runtime/odin.sqlite",
) -> dict[str, object]:
    return MockMT5SymbolMapping(log_path=log_path, sqlite_path=sqlite_path).report()

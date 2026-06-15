import unittest

from odin.contracts.mt5_symbols import (
    MT5SymbolMappingEntry,
    MT5SymbolMappingReport,
    mapped_symbol_key,
    non_asset_key,
    tradable_count_key,
    tradable_key,
)


class A15MT5SymbolContractTests(unittest.TestCase):
    def test_mt5_symbol_entry_serializes(self):
        entry = MT5SymbolMappingEntry(
            odin_symbol="EURUSD",
            mapped_symbol="EURUSD",
            asset_class="forex",
            tradable=True,
            execution_allowed=False,
            reason="mock_fx_symbol",
        )

        payload = entry.to_dict()

        self.assertEqual(payload["odin_symbol"], "EURUSD")
        self.assertEqual(payload[mapped_symbol_key()], "EURUSD")
        self.assertEqual(payload["asset_class"], "forex")
        self.assertIs(payload[tradable_key()], True)
        self.assertIs(payload["execution_allowed"], False)
        self.assertEqual(payload["reason"], "mock_fx_symbol")

    def test_mt5_symbol_report_serializes(self):
        entry = MT5SymbolMappingEntry(
            odin_symbol="VWCE",
            mapped_symbol="non_mt5_fire_asset",
            asset_class="etf",
            tradable=False,
            execution_allowed=False,
            reason="mock_fire_asset_not_platform_tradable",
        )
        report = MT5SymbolMappingReport(
            component="mt5_symbol_mapping",
            status="OK",
            mapping_mode="MOCK_ONLY",
            provider="mt5_mock",
            symbols_count=1,
            forex_symbols_count=0,
            fire_symbols_count=1,
            tradable_count=0,
            non_asset_count=1,
            execution_allowed=False,
            safe_to_trade=False,
            real_trading=False,
            reason="mt5_symbol_mapping_mock_only",
            mappings=[entry],
            notes=["contract test"],
        )

        payload = report.to_dict()

        self.assertEqual(payload["component"], "mt5_symbol_mapping")
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["mapping_mode"], "MOCK_ONLY")
        self.assertEqual(payload["provider"], "mt5_mock")
        self.assertEqual(payload[tradable_count_key()], 0)
        self.assertEqual(payload[non_asset_key()], 1)
        self.assertIs(payload["execution_allowed"], False)
        self.assertIs(payload["safe_to_trade"], False)
        self.assertIs(payload["real_trading"], False)


if __name__ == "__main__":
    unittest.main()

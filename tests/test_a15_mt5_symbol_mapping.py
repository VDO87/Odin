import tempfile
import unittest
from pathlib import Path

from odin.adapters.mt5.symbol_mapping import mt5_symbol_mapping_status
from odin.contracts.mt5_symbols import (
    mapped_symbol_key,
    non_asset_key,
    tradable_count_key,
)
from odin.core.smoke import run_runtime_smoke


class A15MT5SymbolMappingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _status(self):
        return mt5_symbol_mapping_status(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

    def test_mt5_symbol_mapping_returns_ok(self):
        self.assertEqual(self._status()["status"], "OK")

    def test_mt5_symbol_mapping_mode_mock_only(self):
        self.assertEqual(self._status()["mapping_mode"], "MOCK_ONLY")

    def test_mt5_symbol_provider_mock(self):
        self.assertEqual(self._status()["provider"], "mt5_mock")

    def test_mt5_symbol_symbols_count_9(self):
        self.assertEqual(self._status()["symbols_count"], 9)

    def test_mt5_symbol_forex_count_3(self):
        self.assertEqual(self._status()["forex_symbols_count"], 3)

    def test_mt5_symbol_fire_count_6(self):
        self.assertEqual(self._status()["fire_symbols_count"], 6)

    def test_mt5_symbol_tradable_count_3(self):
        self.assertEqual(self._status()[tradable_count_key()], 3)

    def test_mt5_symbol_non_mt5_count_6(self):
        self.assertEqual(self._status()[non_asset_key()], 6)

    def test_eurusd_maps_to_eurusd(self):
        self.assertEqual(_mapping(self._status(), "EURUSD"), "EURUSD")

    def test_usdjpy_maps_to_usdjpy(self):
        self.assertEqual(_mapping(self._status(), "USDJPY"), "USDJPY")

    def test_gbpusd_maps_to_gbpusd(self):
        self.assertEqual(_mapping(self._status(), "GBPUSD"), "GBPUSD")

    def test_vwce_maps_to_non_mt5_fire_asset(self):
        self.assertEqual(_mapping(self._status(), "VWCE"), "non_mt5_fire_asset")

    def test_iwda_maps_to_non_mt5_fire_asset(self):
        self.assertEqual(_mapping(self._status(), "IWDA"), "non_mt5_fire_asset")

    def test_emim_maps_to_non_mt5_fire_asset(self):
        self.assertEqual(_mapping(self._status(), "EMIM"), "non_mt5_fire_asset")

    def test_cspx_maps_to_non_mt5_fire_asset(self):
        self.assertEqual(_mapping(self._status(), "CSPX"), "non_mt5_fire_asset")

    def test_aggh_maps_to_non_mt5_fire_asset(self):
        self.assertEqual(_mapping(self._status(), "AGGH"), "non_mt5_fire_asset")

    def test_xeon_maps_to_non_mt5_fire_asset(self):
        self.assertEqual(_mapping(self._status(), "XEON"), "non_mt5_fire_asset")

    def test_mt5_symbol_execution_allowed_false(self):
        self.assertIs(self._status()["execution_allowed"], False)

    def test_mt5_symbol_safe_to_trade_false(self):
        self.assertIs(self._status()["safe_to_trade"], False)

    def test_mt5_symbol_real_trading_false(self):
        self.assertIs(self._status()["real_trading"], False)

    def test_smoke_includes_mt5_symbols(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )
        names = {str(module["name"]) for module in report["modules"]}

        self.assertIn("mt5-symbols", names)
        self.assertEqual(report["status"], "PASS")

    def test_smoke_modules_count_12(self):
        report = run_runtime_smoke(
            log_path=str(self.root / "logs" / "events.jsonl"),
            sqlite_path=str(self.root / "runtime" / "odin.sqlite"),
        )

        self.assertEqual(report["modules_count"], 12)


def _mapping(report: dict[str, object], symbol: str) -> str:
    for entry in report["mappings"]:
        if entry["odin_symbol"] == symbol:
            return str(entry[mapped_symbol_key()])
    raise AssertionError(f"missing symbol {symbol}")


if __name__ == "__main__":
    unittest.main()

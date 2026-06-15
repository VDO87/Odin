import unittest

from odin.contracts.market_data import Candle, MarketSnapshot, MarketSymbol
from odin.data.symbols import initial_watchlist


class A5MarketDataContractTests(unittest.TestCase):
    def test_watchlist_contains_eurusd(self):
        symbols = {item.symbol for item in initial_watchlist()}

        self.assertIn("EURUSD", symbols)

    def test_watchlist_contains_fire_symbols(self):
        symbols = {item.symbol for item in initial_watchlist()}

        for symbol in ["VWCE", "IWDA", "EMIM", "CSPX", "AGGH", "XEON"]:
            self.assertIn(symbol, symbols)

    def test_market_symbol_contract_defaults_to_no_execution(self):
        symbol = MarketSymbol("EURUSD", "Euro / US Dollar", "forex")

        self.assertEqual(symbol.source, "mock")
        self.assertIs(symbol.execution_allowed, False)

    def test_snapshot_contract_serializes(self):
        snapshot = MarketSnapshot("EURUSD", 1.085, 1.08508, 0.00008, "t", "mock", "OK")

        self.assertEqual(snapshot.to_dict()["symbol"], "EURUSD")
        self.assertEqual(snapshot.to_dict()["quality_status"], "OK")

    def test_candle_contract_serializes(self):
        candle = Candle("EURUSD", "M15", "t", 1.0, 1.1, 0.9, 1.05, 10, 0.1)

        self.assertEqual(candle.to_dict()["timeframe"], "M15")


if __name__ == "__main__":
    unittest.main()


"""A5 watchlist definitions."""

from __future__ import annotations

from odin.contracts.market_data import MarketSymbol


def forex_mock_symbols() -> list[MarketSymbol]:
    return [
        MarketSymbol("EURUSD", "Euro / US Dollar", "forex", tradable=True, notes="Mock FX pair."),
        MarketSymbol("USDJPY", "US Dollar / Japanese Yen", "forex", tradable=True, notes="Mock FX pair."),
        MarketSymbol("GBPUSD", "British Pound / US Dollar", "forex", tradable=True, notes="Mock FX pair."),
    ]


def fire_mock_symbols() -> list[MarketSymbol]:
    return [
        MarketSymbol("VWCE", "Vanguard FTSE All-World UCITS ETF", "etf", notes="Documental FIRE watchlist."),
        MarketSymbol("IWDA", "iShares Core MSCI World UCITS ETF", "etf", notes="Documental FIRE watchlist."),
        MarketSymbol("EMIM", "iShares Core MSCI EM IMI UCITS ETF", "etf", notes="Documental FIRE watchlist."),
        MarketSymbol("CSPX", "iShares Core S&P 500 UCITS ETF", "etf", notes="Documental FIRE watchlist."),
        MarketSymbol("AGGH", "iShares Core Global Aggregate Bond UCITS ETF", "etf", notes="Documental FIRE watchlist."),
        MarketSymbol("XEON", "Xtrackers II EUR Overnight Rate Swap UCITS ETF", "etf", notes="Documental FIRE watchlist."),
    ]


def initial_watchlist() -> list[MarketSymbol]:
    return forex_mock_symbols() + fire_mock_symbols()


def enabled_watchlist() -> list[MarketSymbol]:
    return [symbol for symbol in initial_watchlist() if symbol.enabled]


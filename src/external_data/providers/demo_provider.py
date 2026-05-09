from __future__ import annotations

from datetime import timedelta

from external_data.models import AssetMetadata, EconomicEvent, ExternalQuote
from shared.enums import AssetClass
from shared.utils import make_id, utc_now


class DemoProvider:
    name = "DemoProvider"

    _QUOTES: dict[str, tuple[float, float, float, str]] = {
        "EURUSD": (1.0818, 1.0820, 1.0819, "USD"),
        "GBPUSD": (1.2698, 1.2702, 1.2700, "USD"),
        "SPY": (519.80, 520.20, 520.05, "USD"),
        "AAPL": (197.10, 197.40, 197.22, "USD"),
    }

    _ASSETS: tuple[AssetMetadata, ...] = (
        AssetMetadata(symbol="EURUSD", provider=name, name="Euro / US Dollar", asset_class=AssetClass.FOREX),
        AssetMetadata(symbol="GBPUSD", provider=name, name="British Pound / US Dollar", asset_class=AssetClass.FOREX),
        AssetMetadata(symbol="SPY", provider=name, name="SPDR S&P 500 ETF", asset_class=AssetClass.ETF, exchange="NYSE Arca", currency="USD"),
        AssetMetadata(symbol="AAPL", provider=name, name="Apple Inc.", asset_class=AssetClass.STOCK, exchange="NASDAQ", currency="USD"),
    )

    def is_configured(self) -> bool:
        return True

    def fetch_quote(self, symbol: str) -> ExternalQuote:
        now = utc_now()
        normalized = symbol.upper().strip() or "EURUSD"
        bid, ask, last, currency = self._QUOTES.get(normalized, (100.0, 100.2, 100.1, "USD"))
        return ExternalQuote(
            symbol=normalized,
            provider=self.name,
            timestamp_utc=now,
            bid=bid,
            ask=ask,
            last_price=last,
            currency=currency,
        )

    def fetch_calendar(self) -> list[EconomicEvent]:
        now = utc_now()
        return [
            EconomicEvent(
                event_id=make_id("eco"),
                provider=self.name,
                title="US CPI (Demo)",
                country="US",
                event_time_utc=now + timedelta(hours=6),
                impact="high",
                forecast="3.2%",
                previous="3.1%",
            ),
            EconomicEvent(
                event_id=make_id("eco"),
                provider=self.name,
                title="ECB Rate Decision (Demo)",
                country="EU",
                event_time_utc=now + timedelta(hours=24),
                impact="high",
                forecast="4.00%",
                previous="4.00%",
            ),
        ]

    def search_assets(self, query: str) -> list[AssetMetadata]:
        needle = query.strip().upper()
        if not needle:
            return list(self._ASSETS)
        return [
            asset
            for asset in self._ASSETS
            if needle in asset.symbol.upper() or needle in asset.name.upper()
        ]

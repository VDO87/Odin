from shared.enums import AssetClass, ExecutionVenue, OrderWorkflow, PortfolioBucket


def test_execution_routing_enums_are_declared() -> None:
    assert ExecutionVenue.MT5.value == "MT5"
    assert ExecutionVenue.XTB.value == "XTB"
    assert ExecutionVenue.MANUAL.value == "MANUAL"

    assert AssetClass.FOREX.value == "FOREX"
    assert AssetClass.ETF.value == "ETF"
    assert AssetClass.STOCK.value == "STOCK"
    assert AssetClass.CFD.value == "CFD"
    assert AssetClass.CRYPTO.value == "CRYPTO"
    assert AssetClass.COMMODITY.value == "COMMODITY"
    assert AssetClass.INDEX.value == "INDEX"

    assert PortfolioBucket.SHORT_TERM_TRADING.value == "SHORT_TERM_TRADING"
    assert PortfolioBucket.MEDIUM_TERM_3_5Y.value == "MEDIUM_TERM_3_5Y"
    assert PortfolioBucket.FIRE_LONG_TERM.value == "FIRE_LONG_TERM"

    assert OrderWorkflow.AUTO_DEMO.value == "AUTO_DEMO"
    assert OrderWorkflow.AUTO_REAL.value == "AUTO_REAL"
    assert OrderWorkflow.TELEGRAM_ASSISTED.value == "TELEGRAM_ASSISTED"
    assert OrderWorkflow.MANUAL_CONFIRMATION.value == "MANUAL_CONFIRMATION"

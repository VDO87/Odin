from odin_brokers.broker_router import BrokerRouter


def test_broker_router_blocks_place_order_when_real_disabled() -> None:
    router = BrokerRouter(allow_real_execution=False, primary="XTB", log_root="logs")
    result = router.place_order({"symbol": "EURUSD", "side": "BUY", "volume": 0.1})
    assert result["accepted"] is False
    assert result["reason"] == "BROKER_ALLOW_REAL_EXECUTION_false"

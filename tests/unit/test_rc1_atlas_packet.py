from odin_atlas.decision_packet import DecisionPacket


def test_decision_packet_contains_shadow_only_permission() -> None:
    packet = DecisionPacket.empty(symbol="EURUSD")
    data = packet.to_dict()
    assert data["execution_permission"] == "SHADOW_ONLY"
    assert data["decision_id"]

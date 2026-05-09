from odin_atlas.consensus_engine import ConsensusEngine


def test_consensus_engine_applies_threshold() -> None:
    engine = ConsensusEngine(min_consensus_score=0.65)
    accepted = engine.evaluate({"a": 0.8, "b": 0.7})
    blocked = engine.evaluate({"a": 0.2, "b": 0.3})

    assert accepted["accepted"] is True
    assert blocked["accepted"] is False

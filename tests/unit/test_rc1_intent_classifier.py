from odin_assistant.intent_classifier import IntentClassifier


def test_intent_classifier_maps_read_and_command() -> None:
    clf = IntentClassifier()
    read_intent = clf.classify("Qual é o estado do ODIN?")
    assert read_intent.intent_type == "read"

    cmd_intent = clf.classify("Pausa o ODIN.")
    assert cmd_intent.intent_type == "command"
    assert cmd_intent.intent_name == "PAUSE_ODIN"

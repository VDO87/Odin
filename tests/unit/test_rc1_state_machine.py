from odin_control.state_machine import OdinState, OdinStateMachine


def test_state_machine_transitions_startup_to_running() -> None:
    machine = OdinStateMachine()
    assert machine.state == OdinState.STOPPED
    assert machine.transition(OdinState.STARTING).accepted is True
    assert machine.transition(OdinState.HEALTHCHECK).accepted is True
    assert machine.transition(OdinState.READY).accepted is True
    assert machine.transition(OdinState.RUNNING).accepted is True


def test_state_machine_rejects_invalid_transition() -> None:
    machine = OdinStateMachine()
    result = machine.transition(OdinState.RUNNING)
    assert result.accepted is False
    assert machine.state == OdinState.STOPPED

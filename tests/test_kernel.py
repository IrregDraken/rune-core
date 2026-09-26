from rune.core.agency import ActionRequest
from rune.core.engine import RUNEEngine
from rune.core.model import DeterministicModel
from rune.core.models import ActionStatus, DecisionStatus, EventType


def test_identity_and_input_cycle():
    engine = RUNEEngine(DeterministicModel())

    result = engine.receive("Hello, RUNE.")

    assert engine.state.identity.name == "RUNE"
    assert "Hello, RUNE." in result
    assert [event.type for event in engine.state.events] == [
        EventType.INPUT,
        EventType.OBSERVATION,
    ]


def test_unauthorized_action_is_not_attempted():
    engine = RUNEEngine(DeterministicModel())

    decision, result = engine.request_action(
        ActionRequest(
            intent="turn on the lights",
            capability="home.lights",
            authorized=False,
        ),
        action_id="lights-1",
    )

    assert decision.status is DecisionStatus.DENIED
    assert result.status is ActionStatus.NOT_ATTEMPTED


def test_feasibility_blocks_action():
    engine = RUNEEngine(DeterministicModel())

    decision, result = engine.request_action(
        ActionRequest(
            intent="deploy",
            capability="deployment",
            authorized=True,
            feasible=False,
        ),
        action_id="deploy-1",
    )

    assert decision.status is DecisionStatus.BLOCKED
    assert result.status is ActionStatus.NOT_ATTEMPTED


def test_attempt_is_not_success_until_verified():
    engine = RUNEEngine(DeterministicModel())

    _, attempted = engine.request_action(
        ActionRequest(
            intent="send message",
            capability="messaging.send",
            authorized=True,
        ),
        action_id="message-1",
    )

    assert attempted.status is ActionStatus.ATTEMPTED

    unknown = engine.verify_action(attempted, {"confirmed": False})
    assert unknown.status is ActionStatus.UNKNOWN

    _, attempted_again = engine.request_action(
        ActionRequest(
            intent="send message",
            capability="messaging.send",
            authorized=True,
        ),
        action_id="message-2",
    )
    verified = engine.verify_action(attempted_again, {"confirmed": True})
    assert verified.status is ActionStatus.SUCCEEDED


def test_working_memory_is_bounded():
    engine = RUNEEngine(DeterministicModel())
    engine.memory.capacity = 2

    engine.memory.remember("a", 1)
    engine.memory.remember("b", 2)
    engine.memory.remember("c", 3)

    assert engine.memory.recall("a") is None
    assert engine.memory.recall("b") == 2
    assert engine.memory.recall("c") == 3

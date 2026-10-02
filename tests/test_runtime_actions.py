from rune.core.model import DeterministicModel
from rune.core.node import Capability, NodeInfo, NodeAction
from rune.runtime import RUNERuntime


class FakeNode:
    def __init__(self) -> None:
        self.actions = []

    def info(self) -> NodeInfo:
        return NodeInfo("fake", "test", "test", frozenset({Capability.WINDOW_CONTROL}))

    def can(self, capability: Capability) -> bool:
        return capability is Capability.WINDOW_CONTROL

    def execute(self, action: NodeAction) -> dict:
        self.actions.append(action)
        return {"status": "succeeded"}

    def verify(self, action: NodeAction) -> dict:
        return {"confirmed": True, "status": "verified"}

    def observe(self) -> dict:
        return {"status": "succeeded"}


def test_runtime_requires_authority_before_action() -> None:
    node = FakeNode()
    runtime = RUNERuntime(DeterministicModel(), node=node)

    blocked = runtime.execute_action(
        Capability.WINDOW_CONTROL,
        {"operation": "focus", "hwnd": "1"},
        authorized=False,
    )
    assert blocked["result"]["status"].value == "not_attempted"
    assert node.actions == []

    allowed = runtime.execute_action(
        Capability.WINDOW_CONTROL,
        {"operation": "focus", "hwnd": "1"},
        authorized=True,
    )
    assert allowed["node_result"]["status"] == "succeeded"
    assert allowed["result"]["status"].value == "succeeded"
    assert len(node.actions) == 1

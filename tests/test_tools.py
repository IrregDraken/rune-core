import pytest

from rune.core.tools import ToolCall, ToolRegistry, ToolResult, ToolRisk, ToolSpec


class EchoTool:
    spec = ToolSpec("echo", "Returns its input.", ToolRisk.READ)

    def invoke(self, call: ToolCall) -> ToolResult:
        return ToolResult(call.call_id, call.name, "succeeded", call.arguments)


class DangerousTool:
    spec = ToolSpec(
        "danger",
        "Requires local authority.",
        ToolRisk.DESTRUCTIVE,
        requires_authority=True,
    )

    def invoke(self, call: ToolCall) -> ToolResult:
        return ToolResult(call.call_id, call.name, "succeeded")


def test_registry_invokes_registered_tool() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())
    result = registry.invoke(ToolCall("echo", {"x": 1}, "1"))
    assert result.status == "succeeded"


def test_registry_blocks_unauthorized_tool() -> None:
    registry = ToolRegistry()
    registry.register(DangerousTool())
    result = registry.invoke(ToolCall("danger", {}, "2"))
    assert result.status == "blocked"
    assert result.error == "authorization_required"


def test_registry_rejects_duplicates() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())
    with pytest.raises(ValueError):
        registry.register(EchoTool())

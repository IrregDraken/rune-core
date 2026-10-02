from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol


class ToolRisk(str, Enum):
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    EXTERNAL = "external"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    risk: ToolRisk = ToolRisk.READ
    requires_authority: bool = False
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = ""


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    tool: str
    status: str
    output: Any = None
    error: str | None = None


class Tool(Protocol):
    spec: ToolSpec

    def invoke(self, call: ToolCall) -> ToolResult: ...


class ToolRegistry:
    """Provider-neutral tool boundary.

    Tools are registered explicitly. RUNE can plan against this registry before
    any external API, cloud provider, browser, or connector is wired in.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        name = tool.spec.name.strip()
        if not name:
            raise ValueError("tool name is required")
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def specs(self) -> list[ToolSpec]:
        return [tool.spec for tool in self._tools.values()]

    def invoke(
        self,
        call: ToolCall,
        *,
        authorized: bool = False,
    ) -> ToolResult:
        tool = self.get(call.name)
        if tool is None:
            return ToolResult(call.call_id, call.name, "blocked", error="tool_not_found")
        if tool.spec.requires_authority and not authorized:
            return ToolResult(
                call.call_id,
                call.name,
                "blocked",
                error="authorization_required",
            )
        try:
            return tool.invoke(call)
        except Exception as exc:
            return ToolResult(
                call.call_id,
                call.name,
                "failed",
                error=str(exc),
            )


@dataclass(frozen=True)
class APIConnectorSpec:
    """Description of an external service before credentials are connected."""

    name: str
    base_url: str
    scopes: tuple[str, ...] = ()
    authentication: str = "unconfigured"


class APIConnector(Protocol):
    spec: APIConnectorSpec

    def health(self) -> dict[str, Any]: ...

    def call(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]: ...

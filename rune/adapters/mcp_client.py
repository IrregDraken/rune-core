from __future__ import annotations

"""Optional MCP client adapter.

MCP is a transport for tools, not a replacement for provider-specific policy.
Server definitions must come from trusted local configuration, never tool input.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    url: str | None = None
    command: str | None = None
    args: tuple[str, ...] = ()
    env_names: tuple[str, ...] = ()
    timeout_seconds: float = 30.0
    tool_name_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if bool(self.url) == bool(self.command):
            raise ValueError("configure exactly one MCP URL or command")
        if self.url and not self.url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
            raise ValueError("MCP HTTP endpoints must use HTTPS or loopback")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


class MCPClientAdapter:
    """Connect to one configured MCP server using the official Python SDK.

    Connections are scoped to each operation. This deliberately favours
    lifecycle isolation until persistent-session pooling is introduced.
    """

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config

    def _server(self, client_module: Any) -> Any:
        if self.config.url:
            return self.config.url
        params = getattr(client_module, "StdioServerParameters")
        child_env = {
            name: os.environ[name]
            for name in self.config.env_names
            if os.environ.get(name)
        }
        return params(command=self.config.command, args=list(self.config.args), env=child_env)

    async def _connect_and(self, operation: str, tool_name: str | None = None,
                           arguments: dict[str, Any] | None = None) -> Any:
        try:
            from mcp import Client, StdioServerParameters
        except ImportError as exc:
            raise RuntimeError("mcp_sdk_not_installed_install_rune_core_connectors") from exc

        server = self.config.url
        if server is None:
            child_env = {
                name: os.environ[name]
                for name in self.config.env_names
                if os.environ.get(name)
            }
            server = StdioServerParameters(
                command=self.config.command,
                args=list(self.config.args),
                env=child_env,
            )
        async with Client(server, read_timeout_seconds=self.config.timeout_seconds) as client:
            if operation == "health":
                return await client.list_tools()
            if operation == "list":
                return await client.list_tools()
            if operation == "call":
                if not tool_name:
                    raise ValueError("mcp_tool_name_required")
                available = await client.list_tools()
                if tool_name not in {item.name for item in available.tools}:
                    raise RuntimeError("mcp_tool_not_exposed_by_server")
                result = await client.call_tool(tool_name, arguments or {})
                if result.is_error:
                    raise RuntimeError("mcp_tool_call_failed")
                if result.structured_content is not None:
                    return result.structured_content
                return [
                    {"type": getattr(item, "type", "unknown"),
                     "text": getattr(item, "text", None)}
                    for item in (result.content or [])
                ]
        raise RuntimeError("mcp_operation_not_supported")

    async def health_check(self) -> bool:
        try:
            await self._connect_and("health")
            return True
        except Exception:
            return False

    async def list_tools(self) -> tuple[dict[str, Any], ...]:
        result = await self._connect_and("list")
        return tuple({
            "name": item.name,
            "description": item.description,
            "input_schema": item.inputSchema,
        } for item in result.tools)

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        remote_name = self.config.tool_name_map.get(tool_name, tool_name)
        return await self._connect_and("call", remote_name, arguments)



def attach_mcp_adapter(manager: Any, connector_id: str, config: MCPServerConfig) -> MCPClientAdapter:
    """Attach an explicitly configured MCP server to an existing connector record."""
    key = connector_id.strip().lower()
    if key not in manager.records:
        raise KeyError(f"unknown_connector:{key}")
    adapter = MCPClientAdapter(config)
    manager.adapters[key] = adapter
    return adapter



def attach_configured_mcp_adapters(manager: Any) -> tuple[str, ...]:
    """Load trusted MCP server definitions from RUNE_MCP_SERVERS_JSON.

    This setting is administrator-owned configuration. Tool arguments can never
    choose a command, URL, environment variable, or process argument.
    """
    raw = os.environ.get("RUNE_MCP_SERVERS_JSON", "").strip()
    if not raw:
        return ()
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError("invalid_rune_mcp_servers_json") from None
    if not isinstance(entries, list) or len(entries) > 20:
        raise ValueError("rune_mcp_servers_must_be_a_list_of_at_most_20")
    attached = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid_mcp_server_entry")
        connector_id = str(entry.get("connector_id", "")).strip().lower()
        if not connector_id or connector_id not in manager.records:
            raise ValueError("mcp_connector_id_not_registered")
        config = MCPServerConfig(
            name=str(entry.get("name", connector_id)),
            url=entry.get("url"), command=entry.get("command"),
            args=tuple(entry.get("args", ())),
            env_names=tuple(entry.get("env_names", ())),
            timeout_seconds=float(entry.get("timeout_seconds", 30)),
            tool_name_map=dict(entry.get("tool_name_map", {})),
        )
        attach_mcp_adapter(manager, connector_id, config)
        attached.append(connector_id)
    return tuple(attached)

import asyncio
import sys
import types

import pytest

from rune.adapters.mcp_client import MCPClientAdapter, MCPServerConfig


def test_mcp_server_config_requires_exactly_one_transport():
    with pytest.raises(ValueError, match="exactly one"):
        MCPServerConfig(name="bad")
    with pytest.raises(ValueError, match="exactly one"):
        MCPServerConfig(name="bad", url="https://example.com/mcp", command="python")


def test_mcp_http_requires_tls_unless_loopback():
    with pytest.raises(ValueError, match="HTTPS or loopback"):
        MCPServerConfig(name="bad", url="http://remote.example/mcp")
    assert MCPServerConfig(name="local", url="http://127.0.0.1:8000/mcp")


def test_mcp_client_lists_and_calls_only_exposed_tools(monkeypatch):
    calls = []

    class Tool:
        name = "lookup"
        description = "Lookup"
        inputSchema = {"type": "object"}

    class Result:
        is_error = False
        structured_content = {"ok": True}
        content = []

    class FakeClient:
        def __init__(self, server, **kwargs):
            self.server = server
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def list_tools(self):
            return types.SimpleNamespace(tools=[Tool()])
        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            return Result()

    fake = types.ModuleType("mcp")
    fake.Client = FakeClient
    fake.StdioServerParameters = lambda **kwargs: kwargs
    monkeypatch.setitem(sys.modules, "mcp", fake)

    adapter = MCPClientAdapter(MCPServerConfig(
        name="test", url="https://mcp.example/mcp",
        tool_name_map={"catalogue.lookup": "lookup"},
    ))
    assert asyncio.run(adapter.health_check())
    assert asyncio.run(adapter.invoke("catalogue.lookup", {"id": "1"})) == {"ok": True}
    assert calls == [("lookup", {"id": "1"})]


def test_mcp_client_rejects_tool_not_exposed(monkeypatch):
    class FakeClient:
        def __init__(self, server, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def list_tools(self): return types.SimpleNamespace(tools=[])
    fake = types.ModuleType("mcp")
    fake.Client = FakeClient
    fake.StdioServerParameters = lambda **kwargs: kwargs
    monkeypatch.setitem(sys.modules, "mcp", fake)
    adapter = MCPClientAdapter(MCPServerConfig(name="test", url="https://mcp.example/mcp"))
    with pytest.raises(RuntimeError, match="not_exposed"):
        asyncio.run(adapter.invoke("unknown", {}))



def test_configured_mcp_servers_attach_only_to_registered_connectors(monkeypatch):
    import json
    from types import SimpleNamespace
    from rune.adapters.mcp_client import attach_configured_mcp_adapters
    manager = SimpleNamespace(
        records={"notion": object()},
        adapters={"notion": "direct"},
    )
    monkeypatch.setenv("RUNE_MCP_SERVERS_JSON", json.dumps([{
        "connector_id": "notion",
        "name": "notion-mcp",
        "url": "https://mcp.example/mcp",
        "tool_name_map": {"notion.search": "search"},
    }]))
    attached = attach_configured_mcp_adapters(manager)
    assert attached == ("notion",)
    assert manager.adapters["notion"].config.tool_name_map == {"notion.search": "search"}


def test_configured_mcp_servers_reject_unknown_connector(monkeypatch):
    import json
    from types import SimpleNamespace
    from rune.adapters.mcp_client import attach_configured_mcp_adapters
    manager = SimpleNamespace(records={}, adapters={})
    monkeypatch.setenv("RUNE_MCP_SERVERS_JSON", json.dumps([{
        "connector_id": "not-registered", "url": "https://mcp.example/mcp"
    }]))
    with pytest.raises(ValueError, match="not_registered"):
        attach_configured_mcp_adapters(manager)

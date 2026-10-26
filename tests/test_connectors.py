import asyncio

from rune.core.capabilities import ActionRisk
from rune.core.connectors import (
    ConnectorManager, ConnectorRecord, ConnectorStatus, ExecutionStatus, ToolDefinition,
)


class MockAdapter:
    def __init__(self, outputs=None, fail=0):
        self.outputs = outputs or {"ok": True}
        self.fail = fail
        self.calls = 0

    async def health_check(self):
        return True

    async def invoke(self, tool_name, arguments):
        self.calls += 1
        if self.calls <= self.fail:
            raise RuntimeError("temporary failure")
        return self.outputs


def test_connector_health_and_successful_mock_execution():
    manager = ConnectorManager()
    adapter = MockAdapter()
    manager.register_connector(ConnectorRecord("notion", "mcp"), adapter)
    manager.register_tool(ToolDefinition(
        "notion.page.create", "notion", "create_page",
        "Create a page", {"type": "object", "required": ["title"],
        "properties": {"title": {"type": "string"}}, "additionalProperties": False},
    ))
    assert asyncio.run(manager.health_check("notion")) is ConnectorStatus.HEALTHY
    result = asyncio.run(manager.execute("notion.page.create", {"title": "Plan"}, execution_id="e1"))
    assert result.status is ExecutionStatus.SUCCEEDED_UNVERIFIED
    assert result.output == {"ok": True}
    assert len(manager.audit_log) == 1


def test_disconnected_connector_never_executes():
    manager = ConnectorManager()
    adapter = MockAdapter()
    manager.register_connector(ConnectorRecord("google", "direct_api"), adapter)
    manager.register_tool(ToolDefinition("gmail.search", "google", "search",
                                         "Search mail", {"type": "object"}))
    result = asyncio.run(manager.execute("gmail.search", {}, execution_id="e2"))
    assert result.status is ExecutionStatus.UNAVAILABLE
    assert adapter.calls == 0


def test_high_impact_action_requires_explicit_approval():
    manager = ConnectorManager()
    adapter = MockAdapter()
    manager.register_connector(ConnectorRecord("google", "direct_api"), adapter)
    manager.register_tool(ToolDefinition(
        "gmail.send", "google", "send", "Send mail", {"type": "object"},
        risk=ActionRisk.EXTERNAL_COMMUNICATION,
    ))
    asyncio.run(manager.health_check("google"))
    result = asyncio.run(manager.execute("gmail.send", {}, execution_id="e3"))
    assert result.status is ExecutionStatus.AWAITING_APPROVAL
    assert adapter.calls == 0
    approved = asyncio.run(manager.execute("gmail.send", {}, execution_id="e4", approved=True))
    assert approved.status is ExecutionStatus.SUCCEEDED_UNVERIFIED


def test_schema_failure_and_idempotency():
    manager = ConnectorManager()
    adapter = MockAdapter()
    manager.register_connector(ConnectorRecord("search", "direct_api"), adapter)
    manager.register_tool(ToolDefinition(
        "search.web", "search", "search", "Search",
        {"type": "object", "required": ["query"],
         "properties": {"query": {"type": "string"}}, "additionalProperties": False},
    ))
    asyncio.run(manager.health_check("search"))
    invalid = asyncio.run(manager.execute("search.web", {}, execution_id="e5"))
    assert invalid.status is ExecutionStatus.BLOCKED
    first = asyncio.run(manager.execute("search.web", {"query": "MCP"},
                                  execution_id="e6", idempotency_key="same"))
    second = asyncio.run(manager.execute("search.web", {"query": "MCP"},
                                   execution_id="e7", idempotency_key="same"))
    assert first.status is ExecutionStatus.SUCCEEDED_UNVERIFIED
    assert second.execution_id == "e6"
    assert adapter.calls == 1


def test_bounded_retry():
    manager = ConnectorManager()
    adapter = MockAdapter(fail=1)
    manager.register_connector(ConnectorRecord("search", "direct_api"), adapter)
    manager.register_tool(ToolDefinition(
        "search.web", "search", "search", "Search", {"type": "object"}, max_retries=1,
    ))
    asyncio.run(manager.health_check("search"))
    result = asyncio.run(manager.execute("search.web", {}, execution_id="e8"))
    assert result.status is ExecutionStatus.SUCCEEDED_UNVERIFIED
    assert result.attempts == 2

def test_initial_manager_registers_all_catalogue_tools_without_live_auth():
    from rune.core.connectors import build_initial_connector_manager
    from rune.core.integration_catalogue import integration_catalogue, tool_catalogue

    manager = build_initial_connector_manager()
    assert set(manager.records) == {item.id for item in integration_catalogue()}
    assert set(manager.tools) == {item.id for item in tool_catalogue()}
    assert manager.records["whatsapp"].status is ConnectorStatus.DISCONNECTED
    assert manager.records["instagram"].status is ConnectorStatus.DISCONNECTED
    assert manager.adapters["brave_search"] is not None
    assert manager.adapters["tavily"] is not None
    assert manager.adapters["notion"] is not None
    assert manager.adapters["google_workspace"] is not None
    assert manager.adapters["figma"] is not None
    assert manager.adapters["email_delivery"] is not None
    assert manager.adapters["telegram"] is not None
    assert manager.adapters["github"] is not None
    assert manager.adapters["slack"] is not None
    assert manager.adapters["discord"] is not None

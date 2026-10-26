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



def test_every_tool_has_an_adapter_or_an_explicit_deferred_phase():
    from rune.core.connectors import build_initial_connector_manager
    from rune.core.integration_catalogue import tool_catalogue
    manager = build_initial_connector_manager()
    deferred = {"snapchat", "android_companion"}
    missing = {
        item.integration_id for item in tool_catalogue()
        if item.integration_id not in manager.adapters
    }
    assert missing == deferred
    assert all(
        item.integration_id in manager.adapters or item.integration_id in deferred
        for item in tool_catalogue()
    )



def test_idempotency_key_is_scoped_and_rejects_changed_arguments():
    manager = ConnectorManager()
    adapter = MockAdapter()
    manager.register_connector(ConnectorRecord("service", "direct"), adapter)
    manager.register_tool(ToolDefinition(
        "item.create", "service", "create", "Create item",
        {"type": "object", "required": ["value"],
         "properties": {"value": {"type": "string"}}, "additionalProperties": False},
    ))
    asyncio.run(manager.health_check("service"))
    first = asyncio.run(manager.execute("item.create", {"value": "one"},
        execution_id="one", idempotency_key="same"))
    repeated = asyncio.run(manager.execute("item.create", {"value": "one"},
        execution_id="two", idempotency_key="same"))
    changed = asyncio.run(manager.execute("item.create", {"value": "two"},
        execution_id="three", idempotency_key="same"))
    assert first.status is ExecutionStatus.SUCCEEDED_UNVERIFIED
    assert repeated.execution_id == "one"
    assert changed.status is ExecutionStatus.BLOCKED
    assert changed.error_code == "idempotency_key_reused_with_different_arguments"
    assert adapter.calls == 1


def test_idempotency_keys_are_scoped_to_tool_identity():
    manager = ConnectorManager()
    adapter = MockAdapter()
    manager.register_connector(ConnectorRecord("service", "direct"), adapter)
    schema = {"type": "object", "required": ["value"],
              "properties": {"value": {"type": "string"}}, "additionalProperties": False}
    manager.register_tool(ToolDefinition("item.create", "service", "create", "Create", schema))
    manager.register_tool(ToolDefinition("item.update", "service", "update", "Update", schema))
    asyncio.run(manager.health_check("service"))
    first = asyncio.run(manager.execute("item.create", {"value": "same"},
        execution_id="one", idempotency_key="shared"))
    second = asyncio.run(manager.execute("item.update", {"value": "same"},
        execution_id="two", idempotency_key="shared"))
    assert first.tool_id != second.tool_id
    assert adapter.calls == 2

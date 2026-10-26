import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from types import SimpleNamespace

from rune.api import RUNERequestHandler
from rune.core.authority import Authority
from rune.core.capabilities import ActionRisk
from rune.core.connectors import (
    ConnectorManager, ConnectorRecord, ConnectorStatus, ToolDefinition,
)


class FakeAdapter:
    async def health_check(self):
        return True
    async def invoke(self, tool_name, arguments):
        return {"sent": True, "tool": tool_name}


def _server():
    manager = ConnectorManager()
    adapter = FakeAdapter()
    record = ConnectorRecord("messaging", "direct")
    record.status = ConnectorStatus.HEALTHY
    manager.register_connector(record, adapter)
    manager.register_tool(ToolDefinition(
        "message.send", "messaging", "send", "Send message",
        {"type": "object", "required": ["text"],
         "properties": {"text": {"type": "string"}}, "additionalProperties": False},
        risk=ActionRisk.EXTERNAL_COMMUNICATION, requires_confirmation=True,
    ))
    runtime = SimpleNamespace(authority=Authority("test-session"), connectors=manager)
    RUNERequestHandler.runtime = runtime
    RUNERequestHandler.shell = None
    server = ThreadingHTTPServer(("127.0.0.1", 0), RUNERequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _post(server, path, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-RUNE-Session"] = token
    request = Request(
        f"http://127.0.0.1:{server.server_port}{path}",
        data=json.dumps(payload).encode(), headers=headers, method="POST",
    )
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_connector_execution_api_requires_privileged_session():
    server, thread = _server()
    try:
        status, payload = _post(server, "/api/connectors/execute", {
            "tool_id": "message.send", "execution_id": "unauth", "arguments": {"text": "hello"}
        })
        assert status == 403
        assert payload["error"] == "privileged session required"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_connector_execution_api_returns_approval_then_executes_after_confirmation():
    server, thread = _server()
    try:
        payload = {"tool_id": "message.send", "execution_id": "e1", "arguments": {"text": "hello"}}
        status, result = _post(server, "/api/connectors/execute", payload, "test-session")
        assert status == 200
        assert result["execution"]["status"] == "awaiting_approval"

        payload["execution_id"] = "e2"
        payload["approved"] = True
        status, result = _post(server, "/api/connectors/execute", payload, "test-session")
        assert status == 200
        assert result["execution"]["status"] == "succeeded_unverified"
        assert result["execution"]["verified"] is False
        assert result["execution"]["output"]["sent"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_connector_health_api_requires_session_and_reports_status():
    server, thread = _server()
    try:
        status, _ = _post(server, "/api/connectors/health", {"connector_id": "messaging"})
        assert status == 403
        status, result = _post(server, "/api/connectors/health", {
            "connector_id": "messaging"
        }, "test-session")
        assert status == 200
        assert result["status"] == "healthy"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

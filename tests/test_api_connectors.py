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



def test_messaging_consent_api_requires_session_and_supports_revocation(monkeypatch, tmp_path):
    monkeypatch.setenv("RUNE_CONSENT_DB", str(tmp_path / "consent.sqlite3"))
    server, thread = _server()
    try:
        payload = {"channel": "whatsapp", "recipient": "+2348000000000",
                   "source": "verified consent record"}
        status, _ = _post(server, "/api/consent/opt-in", payload)
        assert status == 403
        status, result = _post(server, "/api/consent/opt-in", payload, "test-session")
        assert status == 200
        assert result["consent"] == "opted_in"
        status, result = _post(server, "/api/consent/revoke", payload, "test-session")
        assert status == 200
        assert result["consent"] == "revoked"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_whatsapp_webhook_get_challenge_verification(monkeypatch):
    from urllib.error import HTTPError
    from urllib.request import urlopen
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-secret")
    server, thread = _server()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=verify-secret&hub.challenge=challenge-123"
        with urlopen(url, timeout=3) as response:
            assert response.status == 200
            assert response.read() == b"challenge-123"
        bad = url.replace("verify-secret", "wrong-token")
        try:
            urlopen(bad, timeout=3)
        except HTTPError as exc:
            assert exc.code == 403
        else:
            raise AssertionError("invalid webhook verification token must be rejected")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_whatsapp_webhook_post_requires_valid_meta_signature(monkeypatch, tmp_path):
    import hashlib
    import hmac
    import time
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "app-secret")
    monkeypatch.setenv("RUNE_CONSENT_DB", str(tmp_path / "consent.sqlite3"))
    server, thread = _server()
    try:
        raw = json.dumps({"entry": [{"changes": [{"value": {"messages": [
            {"from": "2348000000000", "id": "wamid.api-start", "timestamp": str(time.time()), "text": {"body": "START"}}
        ]}}]}]}).encode()
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/webhooks/whatsapp",
            data=raw, headers={"Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=invalid"}, method="POST")
        try:
            urlopen(request, timeout=3)
        except HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("invalid webhook signature must be rejected")

        signature = "sha256=" + hmac.new(b"app-secret", raw, hashlib.sha256).hexdigest()
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/webhooks/whatsapp",
            data=raw, headers={"Content-Type": "application/json",
                "X-Hub-Signature-256": signature}, method="POST")
        with urlopen(request, timeout=3) as response:
            result = json.loads(response.read())
            assert response.status == 200
            assert result == {"status": "accepted", "inbound_recorded": 1,
                              "opted_in": 1, "revoked": 0}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

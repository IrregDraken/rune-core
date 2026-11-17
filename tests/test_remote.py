import json
import httpx

from rune.core.remote import RemoteBackendClient, RemoteBackendError


def test_remote_client_sends_owner_token_and_registers_device():
    seen = {}
    def handler(request):
        seen["authorization"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json={"device": {"id": "device-id"}, "device_token": "once"})
    client = RemoteBackendClient("https://rune.example", "owner-token",
                                 transport=httpx.MockTransport(handler))
    result = client.register_device("Pixel", "android", ["app.list", "ui.observe"])
    assert seen["authorization"] == "Bearer owner-token"
    assert seen["body"]["platform"] == "android"
    assert result["device_token"] == "once"


def test_remote_client_queues_approval_gated_task():
    seen = {}
    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(201, json={"task": {"status": "awaiting_approval"}})
    client = RemoteBackendClient("https://rune.example", "owner-token",
                                 transport=httpx.MockTransport(handler))
    result = client.create_task("device-id", "ui.interact", {"action": "tap"})
    assert seen["body"]["requires_approval"] is True
    assert result["task"]["status"] == "awaiting_approval"


def test_remote_client_requires_credentials():
    try:
        RemoteBackendClient("", "")
    except ValueError as exc:
        assert "RUNE_REMOTE_BACKEND_URL" in str(exc)
    else:
        raise AssertionError("missing backend URL should fail")

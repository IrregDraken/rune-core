from fastapi.testclient import TestClient

from rune_backend.main import app
from rune_backend.routes import _reject_secret_fields, _validate_capability_arguments
from fastapi import HTTPException

client = TestClient(app)


def test_owner_endpoints_require_bearer_token():
    response = client.get("/v1/devices")
    assert response.status_code == 401


def test_task_payload_rejects_passwords_and_tokens_recursively():
    for payload in (
        {"password": "never-send"},
        {"nested": {"refresh_token": "never-send"}},
        {"items": [{"private_key": "never-send"}]},
        {"session-cookie": "never-send"},
    ):
        try:
            _reject_secret_fields(payload)
        except HTTPException as exc:
            assert exc.status_code == 400
        else:
            raise AssertionError("sensitive task payload should be rejected")


def test_task_payload_allows_non_secret_ui_arguments():
    _reject_secret_fields({
        "action": "tap",
        "coordinates": {"x": 100, "y": 250},
        "target": "visible_button",
    })



def test_backend_rejects_unimplemented_device_capabilities():
    try:
        _validate_capability_arguments("shell.execute", {})
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("unimplemented capability should be rejected")


def test_backend_validates_tap_coordinates():
    try:
        _validate_capability_arguments("ui.interact", {"action": "tap", "x": -1, "y": 20})
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("out-of-range tap should be rejected")


def test_backend_accepts_supported_app_launch():
    _validate_capability_arguments("app.launch", {"packageName": "com.example.app"})



def test_remote_task_creation_forces_owner_approval(monkeypatch):
    from uuid import UUID
    from rune_backend.auth import Owner, require_owner
    from rune_backend import routes

    owner_id = UUID("11111111-1111-4111-8111-111111111111")
    device_id = UUID("22222222-2222-4222-8222-222222222222")
    task_id = UUID("33333333-3333-4333-8333-333333333333")
    calls = []

    async def fake_request(method, table, *, params=None, body=None, prefer=None):
        calls.append((method, table, params, body))
        if method == "GET" and table == "rune_devices":
            return [{"id": str(device_id), "capabilities": ["app.launch"]}]
        if method == "POST" and table == "rune_tasks":
            return [{"id": str(task_id), "status": body["status"], **body}]
        return None

    monkeypatch.setattr(routes.store, "request", fake_request)
    app.dependency_overrides[require_owner] = lambda: Owner(owner_id, "owner@example.test")
    try:
        response = client.post("/v1/tasks", json={
            "device_id": str(device_id),
            "capability": "app.launch",
            "arguments": {"packageName": "com.example.app"},
            "expires_in_seconds": 60,
            "requires_approval": False,
        })
    finally:
        app.dependency_overrides.pop(require_owner, None)

    assert response.status_code == 201
    assert response.json()["task"]["status"] == "awaiting_approval"
    inserted = next(call[3] for call in calls if call[0] == "POST" and call[1] == "rune_tasks")
    assert inserted["requires_approval"] is True

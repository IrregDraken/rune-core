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

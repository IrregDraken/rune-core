from fastapi.testclient import TestClient

from rune_backend.main import app

client = TestClient(app)


def test_health_returns_service_status_and_request_id():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "rune-backend"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]


def test_health_preserves_supplied_request_id():
    response = client.get("/health", headers={"X-Request-ID": "test-request-123"})

    assert response.status_code == 200
    assert response.json()["request_id"] == "test-request-123"

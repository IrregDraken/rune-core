import asyncio
import json
from urllib.request import Request

import pytest

from rune.adapters.local_connectors import HomeAssistantAdapter, ScopedFilesystemAdapter


def test_filesystem_adapter_confines_all_operations_to_workspace(tmp_path):
    adapter = ScopedFilesystemAdapter(str(tmp_path))
    result = asyncio.run(adapter.invoke("filesystem.file.write", {
        "path": "notes/today.txt", "content": "RUNE workspace"
    }))
    assert result["bytes_written"] == len("RUNE workspace")
    assert asyncio.run(adapter.invoke("filesystem.file.read", {"path": "notes/today.txt"})) == "RUNE workspace"
    assert asyncio.run(adapter.invoke("filesystem.file.delete", {"path": "notes/today.txt"}))["deleted"]
    with pytest.raises(ValueError, match="outside_root"):
        asyncio.run(adapter.invoke("filesystem.file.read", {"path": "../outside.txt"}))


def test_filesystem_adapter_rejects_symlink_escape(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)
    adapter = ScopedFilesystemAdapter(str(root))
    with pytest.raises(ValueError, match="outside_root"):
        asyncio.run(adapter.invoke("filesystem.file.read", {"path": "escape/secret.txt"}))


def test_home_assistant_entity_read_uses_bearer_auth(monkeypatch):
    from rune.adapters import local_connectors as module
    captured = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"entity_id":"light.office","state":"on"}'
    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()
    async def inline_thread(fn, *args): return fn()
    monkeypatch.setenv("HOME_ASSISTANT_URL", "http://127.0.0.1:8123")
    monkeypatch.setenv("HOME_ASSISTANT_TOKEN", "mock-token")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    result = asyncio.run(HomeAssistantAdapter().invoke(
        "home_assistant.entity.read", {"entity_id": "light.office"}
    ))
    assert result["state"] == "on"
    assert captured[0].get_header("Authorization") == "Bearer mock-token"
    assert captured[0].full_url.endswith("/api/states/light.office")


def test_home_assistant_rejects_invalid_entity_id():
    adapter = HomeAssistantAdapter()
    with pytest.raises(ValueError, match="invalid_entity_id"):
        asyncio.run(adapter.invoke("home_assistant.entity.read", {"entity_id": "../secret"}))

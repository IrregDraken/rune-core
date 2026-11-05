import asyncio
import json


def test_tavily_extract_sends_api_key_and_only_declared_fields(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import TavilyAdapter

    captured = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"results":[{"url":"https://example.com"}]}'

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args):
        return fn()

    monkeypatch.setenv("TAVILY_API_KEY", "private-key")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)

    result = asyncio.run(TavilyAdapter().invoke("tavily.extract", {
        "urls": ["https://example.com"], "extract_depth": "basic",
        "untrusted_extra": "must-not-be-forwarded",
    }))

    assert result["results"][0]["url"] == "https://example.com"
    assert captured[0].full_url == "https://api.tavily.com/extract"
    payload = json.loads(captured[0].data)
    assert payload["api_key"] == "private-key"
    assert payload["urls"] == ["https://example.com"]
    assert payload["extract_depth"] == "basic"
    assert "untrusted_extra" not in payload


def test_notion_search_uses_version_header_and_cursor_fields(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import NotionAdapter

    captured = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"results":[],"has_more":false}'

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args):
        return fn()

    monkeypatch.setenv("NOTION_API_TOKEN", "notion-token")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)

    result = asyncio.run(NotionAdapter().invoke("notion.search", {
        "query": "RUNE", "page_size": 25, "start_cursor": "cursor-1",
    }))

    assert result["has_more"] is False
    assert captured[0].full_url == "https://api.notion.com/v1/search"
    assert captured[0].get_header("Notion-version") == "2022-06-28"
    assert json.loads(captured[0].data) == {
        "query": "RUNE", "page_size": 25, "start_cursor": "cursor-1",
    }


def test_google_contacts_search_uses_people_api_and_requested_fields(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import GoogleWorkspaceAdapter

    adapter = GoogleWorkspaceAdapter()
    captured = []

    async def token():
        return "google-access-token"

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"connections":[]}'

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args):
        return fn()

    monkeypatch.setattr(adapter, "_token", token)
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)

    result = asyncio.run(adapter.invoke("contacts.search", {
        "pageSize": 25, "pageToken": "next-page",
    }))

    assert result["connections"] == []
    assert captured[0].full_url.startswith(
        "https://www.googleapis.com/people/v1/people/me/connections?"
    )
    assert "personFields=names%2CemailAddresses%2CphoneNumbers" in captured[0].full_url
    assert "pageSize=25" in captured[0].full_url
    assert "pageToken=next-page" in captured[0].full_url
    assert captured[0].get_header("Authorization") == "Bearer google-access-token"


def test_spotify_playback_start_uses_put_and_device_target(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import SpotifyAdapter

    adapter = SpotifyAdapter()
    captured = []

    async def access_token():
        return "spotify-access-token"

    class Response:
        status = 204
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b""

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args):
        return fn()

    monkeypatch.setattr(adapter, "_access_token", access_token)
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)

    result = asyncio.run(adapter.invoke("spotify.playback.start", {
        "uri": "spotify:track:abc123", "device_id": "device-1",
    }))

    assert result == {"status": "accepted"}
    assert captured[0].full_url == (
        "https://api.spotify.com/v1/me/player/play?device_id=device-1"
    )
    assert captured[0].get_method() == "PUT"
    assert captured[0].get_header("Authorization") == "Bearer spotify-access-token"
    assert json.loads(captured[0].data) == {"uris": ["spotify:track:abc123"]}


def test_threads_publish_creates_container_then_publishes(monkeypatch):
    from rune.adapters.http_connectors import MetaGraphAdapter

    adapter = MetaGraphAdapter()
    calls = []

    async def request(method, path, body=None):
        calls.append((method, path, body))
        if path.endswith("/threads"):
            return {"id": "container-1"}
        return {"id": "published-1"}

    monkeypatch.setattr(adapter, "_request", request)

    result = asyncio.run(adapter.invoke("threads.post.publish", {
        "user_id": "123456", "text": "RUNE status",
    }))

    assert result == {"id": "published-1"}
    assert calls == [
        ("POST", "/123456/threads", {"text": "RUNE status"}),
        ("POST", "/123456/threads_publish", {"creation_id": "container-1"}),
    ]


def test_home_assistant_service_call_uses_authorised_service_endpoint(monkeypatch):
    from rune.adapters import local_connectors as module
    from rune.adapters.local_connectors import HomeAssistantAdapter

    captured = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'[{"entity_id":"light.office","state":"on"}]'

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args):
        return fn()

    monkeypatch.setenv("HOME_ASSISTANT_URL", "http://homeassistant.local:8123")
    monkeypatch.setenv("HOME_ASSISTANT_TOKEN", "ha-token")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)

    result = asyncio.run(HomeAssistantAdapter().invoke(
        "home_assistant.service.call",
        {"domain": "light", "service": "turn_on", "entity_id": "light.office",
         "service_data": {"brightness": 120}},
    ))

    assert result[0]["state"] == "on"
    assert captured[0].full_url == (
        "http://homeassistant.local:8123/api/services/light/turn_on"
    )
    assert captured[0].get_method() == "POST"
    assert captured[0].get_header("Authorization") == "Bearer ha-token"
    assert json.loads(captured[0].data) == {
        "brightness": 120, "entity_id": "light.office",
    }


def test_scoped_filesystem_write_and_delete_stay_inside_workspace(tmp_path):
    from rune.adapters.local_connectors import ScopedFilesystemAdapter

    adapter = ScopedFilesystemAdapter(str(tmp_path / "workspace"))

    written = asyncio.run(adapter.invoke("filesystem.file.write", {
        "path": "notes/rune.txt", "content": "RUNE checkpoint",
    }))
    target = tmp_path / "workspace" / "notes" / "rune.txt"

    assert written == {"path": "notes/rune.txt", "bytes_written": 15}
    assert target.read_text() == "RUNE checkpoint"

    deleted = asyncio.run(adapter.invoke("filesystem.file.delete", {
        "path": "notes/rune.txt",
    }))
    assert deleted == {"deleted": True, "path": "notes/rune.txt"}
    assert not target.exists()

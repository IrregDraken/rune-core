import os

import pytest

from rune.adapters.http_connectors import BraveSearchAdapter, NotionAdapter, TavilyAdapter


def test_search_adapters_fail_closed_without_credentials(monkeypatch):
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert not __import__("asyncio").run(BraveSearchAdapter().health_check())
    assert not __import__("asyncio").run(TavilyAdapter().health_check())


def test_notion_adapter_requires_credential(monkeypatch):
    monkeypatch.delenv("NOTION_API_TOKEN", raising=False)
    adapter = NotionAdapter()
    assert not __import__("asyncio").run(adapter.health_check())


def test_brave_operation_registry_is_allowlisted():
    adapter = BraveSearchAdapter()
    assert "brave.search" in adapter.operations
    assert "arbitrary.url.fetch" not in adapter.operations


def test_tavily_operation_registry_is_allowlisted():
    adapter = TavilyAdapter()
    assert {"tavily.search", "tavily.extract"} == set(adapter.operations)



def test_notion_database_query_does_not_mutate_shared_operations(monkeypatch):
    adapter = NotionAdapter()
    original = dict(adapter.operations)
    captured = []

    async def capture(operation, arguments):
        captured.append(operation)

    monkeypatch.setattr(adapter, "invoke_operation", capture)
    asyncio = __import__("asyncio")
    asyncio.run(adapter.invoke("notion.database.query", {"database_id": "abc123"}))
    assert captured[0].path == "/databases/abc123/query"
    assert adapter.operations == original


def test_figma_file_lookup_does_not_mutate_shared_operations(monkeypatch):
    from rune.adapters.http_connectors import FigmaAdapter

    adapter = FigmaAdapter()
    original = dict(adapter.operations)
    captured = []

    async def capture(operation, arguments):
        captured.append(operation)

    monkeypatch.setattr(adapter, "invoke_operation", capture)
    __import__("asyncio").run(adapter.invoke("figma.file.get", {"file_key": "file_123"}))
    assert captured[0].path == "/files/file_123"
    assert adapter.operations == original



def test_notion_page_update_uses_validated_page_path_without_mutation(monkeypatch):
    adapter = NotionAdapter()
    original = dict(adapter.operations)
    captured = []

    async def capture(operation, arguments):
        captured.append(operation)

    monkeypatch.setattr(adapter, "invoke_operation", capture)
    __import__("asyncio").run(adapter.invoke(
        "notion.page.update", {"page_id": "abc123", "archived": True}
    ))
    assert captured[0].method == "PATCH"
    assert captured[0].path == "/pages/abc123"
    assert adapter.operations == original


def test_google_workspace_routes_gmail_and_calendar_writes(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import GoogleWorkspaceAdapter

    adapter = GoogleWorkspaceAdapter()
    async def token():
        return "test-token"
    monkeypatch.setattr(adapter, "_token", token)
    captured = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"id":"mock"}'

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args):
        return fn()

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)

    import asyncio
    asyncio.run(adapter.invoke("gmail.draft", {
        "to": "test@example.com", "subject": "Hello", "body": "Draft body"
    }))
    assert captured[-1].full_url.endswith("/gmail/v1/users/me/drafts")
    assert captured[-1].get_method() == "POST"

    asyncio.run(adapter.invoke("calendar.create", {
        "summary": "Planning", "start": {"dateTime": "2026-10-27T10:00:00Z"},
        "end": {"dateTime": "2026-10-27T10:30:00Z"}
    }))
    assert captured[-1].full_url.endswith("/calendar/v3/calendars/primary/events")
    assert captured[-1].get_method() == "POST"

    asyncio.run(adapter.invoke("calendar.update", {
        "event_id": "event123", "summary": "Updated"
    }))
    assert captured[-1].full_url.endswith("/calendar/v3/calendars/primary/events/event123")
    assert captured[-1].get_method() == "PATCH"



def test_resend_adapter_is_allowlisted_and_requires_key(monkeypatch):
    from rune.adapters.http_connectors import ResendAdapter
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    adapter = ResendAdapter()
    assert not __import__("asyncio").run(adapter.health_check())
    assert set(adapter.operations) == {"email.send"}


def test_resend_adapter_sends_only_declared_fields(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import ResendAdapter
    adapter = ResendAdapter()
    captured = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"id":"email_mock"}'

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args):
        return fn()

    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    result = __import__("asyncio").run(adapter.invoke("email.send", {
        "from": "RUNE <noreply@example.com>", "to": ["user@example.com"],
        "subject": "Test", "text": "Hello", "unexpected": "must-not-pass"
    }))
    assert result["id"] == "email_mock"
    assert captured[0].full_url == "https://api.resend.com/emails"
    assert b"unexpected" not in captured[0].data



def test_telegram_bot_adapter_uses_official_send_message_endpoint(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import TelegramBotAdapter
    import asyncio
    adapter = TelegramBotAdapter()
    captured = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"ok":true,"result":{"message_id":7}}'

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args):
        return fn()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "mock-secret")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    result = asyncio.run(adapter.invoke("telegram.message.send", {
        "chat_id": "12345", "text": "Hello", "unexpected": "discard"
    }))
    assert result["message_id"] == 7
    assert captured[0].full_url.endswith("/botmock-secret/sendMessage")
    assert b"unexpected" not in captured[0].data


def test_telegram_adapter_rejects_unknown_operation_and_missing_credentials(monkeypatch):
    from rune.adapters.http_connectors import TelegramBotAdapter
    import asyncio
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    adapter = TelegramBotAdapter()
    assert not asyncio.run(adapter.health_check())
    with pytest.raises(RuntimeError, match="tool_operation_not_implemented"):
        asyncio.run(adapter.invoke("telegram.other", {"chat_id": "1", "text": "x"}))



def test_github_adapter_routes_issue_and_pr_calls(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import GitHubAdapter
    import asyncio
    adapter = GitHubAdapter()
    captured = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"number":12}'

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args):
        return fn()

    monkeypatch.setenv("GITHUB_TOKEN", "mock-token")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    asyncio.run(adapter.invoke("github.issue.create", {
        "owner": "acme", "repo": "project", "title": "Bug"
    }))
    assert captured[-1].full_url == "https://api.github.com/repos/acme/project/issues"
    assert captured[-1].get_method() == "POST"
    asyncio.run(adapter.invoke("github.pull_request.create", {
        "owner": "acme", "repo": "project", "title": "Feature",
        "head": "feature", "base": "main"
    }))
    assert captured[-1].full_url == "https://api.github.com/repos/acme/project/pulls"


def test_github_adapter_rejects_path_injection(monkeypatch):
    from rune.adapters.http_connectors import GitHubAdapter
    import asyncio
    monkeypatch.setenv("GITHUB_TOKEN", "mock-token")
    with pytest.raises(ValueError, match="invalid_github_repository"):
        asyncio.run(GitHubAdapter().invoke("github.issue.create", {
            "owner": "../attacker", "repo": "repo", "title": "x"
        }))



def test_slack_adapter_routes_search_and_send(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import SlackAdapter
    import asyncio
    adapter = SlackAdapter()
    captured = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"ok":true,"messages":{"matches":[]}}'

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args):
        return fn()

    monkeypatch.setenv("SLACK_BOT_TOKEN", "mock-token")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    asyncio.run(adapter.invoke("slack.search", {"query": "from:me", "count": 5}))
    assert captured[-1].full_url.startswith("https://slack.com/api/search.messages?")
    asyncio.run(adapter.invoke("slack.message.send", {"channel": "C123", "text": "Hello"}))
    assert captured[-1].full_url == "https://slack.com/api/chat.postMessage"
    assert captured[-1].get_method() == "POST"


def test_discord_adapter_uses_bot_auth_and_validates_channel(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import DiscordBotAdapter
    import asyncio
    adapter = DiscordBotAdapter()
    captured = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"id":"message123"}'

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args):
        return fn()

    monkeypatch.setenv("DISCORD_BOT_TOKEN", "mock-token")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    asyncio.run(adapter.invoke("discord.message.send", {"channel_id": "123456", "content": "Hello"}))
    assert captured[-1].full_url == "https://discord.com/api/v10/channels/123456/messages"
    assert captured[-1].get_header("Authorization") == "Bot mock-token"
    with pytest.raises(ValueError, match="invalid_discord_message"):
        asyncio.run(adapter.invoke("discord.message.send", {"channel_id": "bad/id", "content": "x"}))



def test_dropbox_adapter_refreshes_oauth_and_searches_files(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import DropboxAdapter
    import asyncio
    adapter = DropboxAdapter()
    requests = []

    class Response:
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return self.payload

    def fake_urlopen(request, timeout):
        requests.append(request)
        if request.full_url.endswith("/oauth2/token"):
            return Response(b'{"access_token":"mock-access","expires_in":3600}')
        return Response(b'{"matches":[]}')

    async def inline_thread(fn, *args): return fn()

    monkeypatch.setenv("DROPBOX_APP_KEY", "key")
    monkeypatch.setenv("DROPBOX_APP_SECRET", "secret")
    monkeypatch.setenv("DROPBOX_REFRESH_TOKEN", "refresh")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    result = asyncio.run(adapter.invoke("dropbox.files.search", {"query": "notes"}))
    assert result == {"matches": []}
    assert requests[0].full_url == "https://api.dropbox.com/oauth2/token"
    assert requests[1].full_url == "https://api.dropboxapi.com/2/files/search_v2"
    assert requests[1].get_header("Authorization") == "Bearer mock-access"



def test_google_drive_upload_uses_multipart_and_size_guard(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import GoogleWorkspaceAdapter
    import asyncio, base64
    adapter = GoogleWorkspaceAdapter()
    captured = []

    async def token(): return "mock-token"
    monkeypatch.setattr(adapter, "_token", token)

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"id":"file1","name":"notes.txt"}'

    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()

    async def inline_thread(fn, *args): return fn()
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    result = asyncio.run(adapter.invoke("drive.upload", {
        "file_name": "notes.txt", "mime_type": "text/plain",
        "content_base64": base64.b64encode(b"hello").decode()
    }))
    assert result["id"] == "file1"
    assert captured[0].full_url.startswith("https://www.googleapis.com/upload/drive/v3/files?")
    assert "multipart/related" in captured[0].get_header("Content-type")
    assert b"hello" in captured[0].data
    with pytest.raises(ValueError, match="invalid_base64"):
        asyncio.run(adapter.invoke("drive.upload", {
            "file_name": "bad.txt", "mime_type": "text/plain", "content_base64": "not base64!"
        }))



def test_youtube_search_uses_api_key_and_fixed_part(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import YouTubeAdapter
    import asyncio
    captured = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"items":[]}'
    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()
    async def inline_thread(fn, *args): return fn()
    monkeypatch.setenv("YOUTUBE_API_KEY", "mock-key")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    result = asyncio.run(YouTubeAdapter().invoke("youtube.search", {"q": "RUNE", "maxResults": 5}))
    assert result == {"items": []}
    assert "key=mock-key" in captured[0].full_url
    assert "part=snippet" in captured[0].full_url


def test_zotero_search_requires_user_id_and_uses_key_header(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import ZoteroAdapter
    import asyncio
    captured = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'[]'
    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()
    async def inline_thread(fn, *args): return fn()
    monkeypatch.setenv("ZOTERO_API_KEY", "mock-key")
    monkeypatch.setenv("ZOTERO_USER_ID", "123")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    assert asyncio.run(ZoteroAdapter().invoke("zotero.items.search", {"q": "memory"})) == []
    assert captured[0].get_header("Zotero-api-key") == "mock-key"
    assert "/users/123/items?" in captured[0].full_url


def test_spotify_adapter_rejects_missing_credentials(monkeypatch):
    from rune.adapters.http_connectors import SpotifyAdapter
    import asyncio
    for key in ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REFRESH_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    assert not asyncio.run(SpotifyAdapter().health_check())



def test_railway_logs_uses_public_graphql_endpoint_and_bounded_limit(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import RailwayAdapter
    import asyncio
    captured = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"data":{"deploymentLogs":[]}}'
    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()
    async def inline_thread(fn, *args): return fn()
    monkeypatch.setenv("RAILWAY_API_TOKEN", "mock-token")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    result = asyncio.run(RailwayAdapter().invoke("railway.logs.read", {
        "deploymentId": "deploy_123", "lines": 9999
    }))
    assert result == {"deploymentLogs": []}
    assert captured[0].full_url == "https://backboard.railway.com/graphql/v2"
    payload = __import__("json").loads(captured[0].data)
    assert payload["variables"]["limit"] == 500


def test_hubspot_contact_search_maps_q_to_query(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import HubSpotAdapter
    import asyncio, json
    captured = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"results":[]}'
    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()
    async def inline_thread(fn, *args): return fn()
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "mock-token")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    asyncio.run(HubSpotAdapter().invoke("hubspot.contacts.search", {"q": "Ada", "limit": 10}))
    body = json.loads(captured[0].data)
    assert body == {"query": "Ada", "limit": 10}
    assert captured[0].full_url.endswith("/crm/v3/objects/contacts/search")



def test_meta_graph_instagram_publish_runs_container_then_publish(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import MetaGraphAdapter
    import asyncio, json
    calls = []
    class Response:
        def __init__(self, payload): self.payload = payload
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return self.payload
    def fake_urlopen(request, timeout):
        calls.append(request)
        if request.full_url.endswith("/media"):
            return Response(b'{"id":"container1"}')
        return Response(b'{"id":"published1"}')
    async def inline_thread(fn, *args): return fn()
    monkeypatch.setenv("META_ACCESS_TOKEN", "mock-token")
    monkeypatch.setenv("META_GRAPH_VERSION", "v99.0")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    result = asyncio.run(MetaGraphAdapter().invoke("instagram.media.publish", {
        "ig_user_id": "12345", "image_url": "https://cdn.example/image.jpg", "caption": "hello"
    }))
    assert result["id"] == "published1"
    assert calls[0].full_url.endswith("/v99.0/12345/media")
    assert calls[1].full_url.endswith("/v99.0/12345/media_publish")
    assert json.loads(calls[1].data)["creation_id"] == "container1"


def test_x_api_post_uses_bearer_and_reply_contract(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import XApiAdapter
    import asyncio, json
    captured = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"data":{"id":"post1"}}'
    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()
    async def inline_thread(fn, *args): return fn()
    monkeypatch.setenv("X_ACCESS_TOKEN", "mock-token")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    asyncio.run(XApiAdapter().invoke("x.post.create", {"text": "hello", "reply_to_id": "123"}))
    body = json.loads(captured[0].data)
    assert body == {"text": "hello", "reply": {"in_reply_to_tweet_id": "123"}}
    assert captured[0].get_header("Authorization") == "Bearer mock-token"


def test_pinterest_pin_adapter_posts_to_v5(monkeypatch):
    from rune.adapters import http_connectors as module
    from rune.adapters.http_connectors import PinterestAdapter
    import asyncio
    captured = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"id":"pin1"}'
    def fake_urlopen(request, timeout):
        captured.append(request)
        return Response()
    async def inline_thread(fn, *args): return fn()
    monkeypatch.setenv("PINTEREST_ACCESS_TOKEN", "mock-token")
    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.asyncio, "to_thread", inline_thread)
    result = asyncio.run(PinterestAdapter().invoke("pinterest.pin.create", {
        "board_id": "board1", "title": "Design", "media_source": {"source_type": "image_url", "url": "https://cdn.example/a.png"}
    }))
    assert result["id"] == "pin1"
    assert captured[0].full_url == "https://api.pinterest.com/v5/pins"

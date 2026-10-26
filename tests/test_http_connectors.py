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

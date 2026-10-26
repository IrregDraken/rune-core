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

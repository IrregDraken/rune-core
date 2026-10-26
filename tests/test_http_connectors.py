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

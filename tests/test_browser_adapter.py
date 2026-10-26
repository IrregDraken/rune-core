import pytest

from rune.adapters.browser import PlaywrightBrowserAdapter, validate_public_http_url


def test_browser_url_rejects_non_http_schemes_and_local_hosts():
    for value in ("file:///etc/passwd", "javascript:alert(1)", "http://localhost:8000", "http://127.0.0.1"):
        with pytest.raises(ValueError):
            validate_public_http_url(value)


def test_browser_url_rejects_credentials_and_private_ip_literals():
    for value in ("https://user:pass@example.com", "http://10.0.0.1", "http://192.168.1.1"):
        with pytest.raises(ValueError):
            validate_public_http_url(value)


def test_browser_url_checks_resolved_addresses(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", 443))
    ])
    with pytest.raises(ValueError, match="private_destination"):
        validate_public_http_url("https://example.invalid")


def test_browser_adapter_is_disabled_without_enforced_egress_policy(monkeypatch):
    import asyncio
    monkeypatch.delenv("RUNE_BROWSER_EGRESS_POLICY", raising=False)
    adapter = PlaywrightBrowserAdapter()
    assert not asyncio.run(adapter.health_check())
    with pytest.raises(RuntimeError, match="egress_policy_not_enforced"):
        asyncio.run(adapter.invoke("browser.navigate", {"url": "https://example.com"}))

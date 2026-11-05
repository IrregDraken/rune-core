from __future__ import annotations

"""Isolated Playwright adapter with outbound-network destination checks."""

import asyncio
import ipaddress
import os
import re
import socket
from typing import Any
from urllib.parse import urlparse


def validate_public_http_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("browser_url_must_be_http_or_https")
    if parsed.username or parsed.password:
        raise ValueError("browser_url_credentials_not_allowed")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise ValueError("browser_private_destination_blocked")
    try:
        address = ipaddress.ip_address(host)
        if not address.is_global:
            raise ValueError("browser_private_destination_blocked")
    except ValueError as exc:
        if str(exc) == "browser_private_destination_blocked":
            raise
        # A non-IP hostname is resolved and checked again for every request.
        try:
            resolved = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        except OSError:
            raise ValueError("browser_host_resolution_failed") from None
        for item in resolved:
            ip = ipaddress.ip_address(item[4][0])
            if not ip.is_global:
                raise ValueError("browser_private_destination_blocked")
    return value


class PlaywrightBrowserAdapter:
    """Short-lived isolated browser sessions; no persistent user profile."""

    def __init__(self, timeout_ms: int = 20000, max_text_chars: int = 20000) -> None:
        self.timeout_ms = timeout_ms
        self.max_text_chars = max_text_chars

    async def health_check(self) -> bool:
        if os.environ.get("RUNE_BROWSER_EGRESS_POLICY", "").strip().lower() != "enforced":
            return False
        try:
            import playwright.async_api  # noqa: F401
            return True
        except ImportError:
            return False

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name not in {"browser.navigate", "browser.form.submit"}:
            raise RuntimeError("tool_operation_not_implemented")
        if os.environ.get("RUNE_BROWSER_EGRESS_POLICY", "").strip().lower() != "enforced":
            raise RuntimeError("browser_egress_policy_not_enforced")
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("playwright_not_installed_install_rune_core_browser") from exc
        target = await asyncio.to_thread(validate_public_http_url, str(arguments.get("url", "")))
        async with async_playwright() as runtime:
            browser = await runtime.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    accept_downloads=False, java_script_enabled=True,
                    service_workers="block", ignore_https_errors=False,
                )
                async def guard(route: Any) -> None:
                    try:
                        await asyncio.to_thread(validate_public_http_url, route.request.url)
                    except ValueError:
                        await route.abort("blockedbyclient")
                    else:
                        await route.continue_()
                await context.route("**/*", guard)
                page = await context.new_page()
                page.set_default_timeout(self.timeout_ms)
                await page.goto(target, wait_until="domcontentloaded")
                if tool_name == "browser.form.submit":
                    fields = arguments.get("fields", {})
                    if not isinstance(fields, dict) or len(fields) > 50:
                        raise ValueError("invalid_browser_form_fields")
                    for name, value in fields.items():
                        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:-]{0,127}", name):
                            raise ValueError("invalid_browser_field_name")
                        selector = f'[name="{name}"]'
                        await page.locator(selector).first.fill(str(value)[:4000])
                    forms = page.locator("form")
                    if await forms.count() == 0:
                        raise RuntimeError("browser_form_not_found")
                    await forms.first.evaluate("(form) => form.requestSubmit()")
                    await page.wait_for_load_state("domcontentloaded")
                text = await page.locator("body").inner_text()
                return {
                    "url": page.url,
                    "title": await page.title(),
                    "text": text[:self.max_text_chars],
                }
            finally:
                await browser.close()

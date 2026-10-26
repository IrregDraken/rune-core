from __future__ import annotations

"""Small, dependency-free JSON HTTP adapters for supported official APIs.

Only fixed provider base URLs and explicitly registered paths are callable.
No arbitrary URL tool is exposed. Credentials are read from the process
environment at invocation time and are never included in results or logs.
"""

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HttpOperation:
    method: str
    path: str
    query_keys: tuple[str, ...] = ()
    body_keys: tuple[str, ...] = ()


class JsonHttpAdapter:
    def __init__(
        self,
        *,
        base_url: str,
        credential_env: str,
        operations: dict[str, HttpOperation],
        auth_header: str = "Authorization",
        auth_scheme: str = "Bearer",
        fixed_headers: dict[str, str] | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.credential_env = credential_env
        self.operations = operations
        self.auth_header = auth_header
        self.auth_scheme = auth_scheme
        self.fixed_headers = fixed_headers or {}
        self.timeout = timeout

    def _credential(self) -> str:
        value = os.environ.get(self.credential_env, "").strip()
        if not value:
            raise RuntimeError("connector_credentials_missing")
        return value

    async def health_check(self) -> bool:
        return bool(os.environ.get(self.credential_env, "").strip())

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        operation = self.operations.get(tool_name)
        if operation is None:
            raise RuntimeError("tool_operation_not_implemented")
        return await self.invoke_operation(operation, arguments)

    async def invoke_operation(self, operation: HttpOperation, arguments: dict[str, Any]) -> Any:
        credential = self._credential()
        query = {key: arguments[key] for key in operation.query_keys if key in arguments}
        body = {key: arguments[key] for key in operation.body_keys if key in arguments}
        url = self.base_url + operation.path
        if query:
            url += "?" + urlencode(query, doseq=True)
        headers = {"Accept": "application/json", **self.fixed_headers}
        headers[self.auth_header] = (
            f"{self.auth_scheme} {credential}".strip() if self.auth_scheme else credential
        )
        data = json.dumps(body).encode("utf-8") if operation.method.upper() != "GET" else None
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=operation.method.upper())

        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode("utf-8")) if raw else {}
            except HTTPError as exc:
                # Do not leak response bodies, request headers or secrets.
                raise RuntimeError(f"provider_http_{exc.code}") from None
            except (URLError, TimeoutError):
                raise RuntimeError("provider_unreachable") from None

        return await asyncio.to_thread(send)


class BraveSearchAdapter(JsonHttpAdapter):
    def __init__(self) -> None:
        super().__init__(
            base_url="https://api.search.brave.com/res/v1",
            credential_env="BRAVE_SEARCH_API_KEY",
            auth_header="X-Subscription-Token",
            auth_scheme="",
            operations={
                "brave.search": HttpOperation(
                    "GET", "/web/search",
                    query_keys=("q", "count", "country", "search_lang", "freshness"),
                ),
            },
        )


class TavilyAdapter(JsonHttpAdapter):
    def __init__(self) -> None:
        # Tavily accepts the API key in its JSON request body.
        super().__init__(
            base_url="https://api.tavily.com",
            credential_env="TAVILY_API_KEY",
            auth_header="X-Tavily-Connector-Key",
            auth_scheme="",
            operations={
                "tavily.search": HttpOperation(
                    "POST", "/search",
                    body_keys=("query", "search_depth", "topic", "max_results",
                               "include_answer", "include_raw_content", "include_domains",
                               "exclude_domains"),
                ),
                "tavily.extract": HttpOperation(
                    "POST", "/extract",
                    body_keys=("urls", "include_images", "extract_depth", "format"),
                ),
            },
        )

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        # Tavily's documented API authenticates with api_key in the JSON body.
        operation = self.operations.get(tool_name)
        if operation is None:
            raise RuntimeError("tool_operation_not_implemented")
        credential = self._credential()
        body = {key: arguments[key] for key in operation.body_keys if key in arguments}
        body["api_key"] = credential
        url = self.base_url + operation.path
        request = Request(
            url, data=json.dumps(body).encode("utf-8"),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method=operation.method,
        )

        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode("utf-8")) if raw else {}
            except HTTPError as exc:
                raise RuntimeError(f"provider_http_{exc.code}") from None
            except (URLError, TimeoutError):
                raise RuntimeError("provider_unreachable") from None

        return await asyncio.to_thread(send)


class NotionAdapter(JsonHttpAdapter):
    def __init__(self) -> None:
        super().__init__(
            base_url="https://api.notion.com/v1",
            credential_env="NOTION_API_TOKEN",
            fixed_headers={"Notion-Version": "2022-06-28"},
            operations={
                "notion.search": HttpOperation(
                    "POST", "/search", body_keys=("query", "filter", "sort", "page_size", "start_cursor"),
                ),
                "notion.database.query": HttpOperation(
                    "POST", "/databases/{database_id}/query",
                    body_keys=("filter", "sorts", "page_size", "start_cursor"),
                ),
            },
        )

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        operation = self.operations.get(tool_name)
        if operation is None:
            raise RuntimeError("tool_operation_not_implemented")
        if tool_name == "notion.database.query":
            database_id = str(arguments.get("database_id", "")).strip()
            if not database_id or any(ch not in "0123456789abcdefABCDEF-" for ch in database_id):
                raise ValueError("invalid_database_id")
            operation = HttpOperation(
                "POST", f"/databases/{database_id}/query",
                body_keys=("filter", "sorts", "page_size", "start_cursor"),
            )
        return await self.invoke_operation(operation, arguments)

class GoogleWorkspaceAdapter:
    """Google Workspace REST adapter using an OAuth refresh-token grant."""

    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_ROOT = "https://www.googleapis.com"

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._expires_at = 0.0
        self.timeout = 20.0
        self.operations = {
            "gmail.search": ("GET", "/gmail/v1/users/me/messages", ("q", "maxResults")),
            "calendar.search": ("GET", "/calendar/v3/calendars/primary/events", ("timeMin", "timeMax", "q", "maxResults")),
            "drive.search": ("GET", "/drive/v3/files", ("q", "pageSize", "orderBy", "fields")),
            "contacts.search": ("GET", "/people/v1/people/me/connections", ("pageSize", "personFields")),
        }

    async def health_check(self) -> bool:
        return all(os.environ.get(key, "").strip() for key in (
            "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"
        ))

    async def _token(self) -> str:
        import time
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token
        from urllib.parse import urlencode
        data = urlencode({
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "refresh_token": os.environ.get("GOOGLE_REFRESH_TOKEN", ""),
            "grant_type": "refresh_token",
        }).encode()
        request = Request(self.TOKEN_URL, data=data,
                          headers={"Content-Type": "application/x-www-form-urlencoded"},
                          method="POST")
        def refresh() -> dict:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                raise RuntimeError(f"google_oauth_http_{exc.code}") from None
            except (URLError, TimeoutError):
                raise RuntimeError("google_oauth_unreachable") from None
        payload = await asyncio.to_thread(refresh)
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("google_oauth_token_missing")
        self._access_token = str(token)
        self._expires_at = time.time() + int(payload.get("expires_in", 3600))
        return self._access_token

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        operation = self.operations.get(tool_name)
        if operation is None:
            raise RuntimeError("tool_operation_not_implemented")
        method, path, query_keys = operation
        query = {key: arguments[key] for key in query_keys if key in arguments}
        url = self.API_ROOT + path + (("?" + urlencode(query, doseq=True)) if query else "")
        token = await self._token()
        request = Request(url, headers={"Authorization": f"Bearer {token}",
                                        "Accept": "application/json"}, method=method)
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode("utf-8")) if raw else {}
            except HTTPError as exc:
                raise RuntimeError(f"google_api_http_{exc.code}") from None
            except (URLError, TimeoutError):
                raise RuntimeError("google_api_unreachable") from None
        return await asyncio.to_thread(send)


class FigmaAdapter(JsonHttpAdapter):
    def __init__(self) -> None:
        super().__init__(
            base_url="https://api.figma.com/v1",
            credential_env="FIGMA_ACCESS_TOKEN",
            auth_header="X-Figma-Token",
            auth_scheme="",
            operations={
                "figma.file.get": HttpOperation("GET", "/files/{file_key}"),
                "figma.comments.list": HttpOperation("GET", "/files/{file_key}/comments"),
            },
        )

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        operation = self.operations.get(tool_name)
        if operation is None:
            raise RuntimeError("tool_operation_not_implemented")
        file_key = str(arguments.get("file_key", "")).strip()
        if not file_key or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in file_key):
            raise ValueError("invalid_file_key")
        operation = HttpOperation(
            operation.method, operation.path.replace("{file_key}", file_key),
            operation.query_keys, operation.body_keys,
        )
        return await self.invoke_operation(operation, arguments)

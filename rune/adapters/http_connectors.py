from __future__ import annotations

"""Small, dependency-free JSON HTTP adapters for supported official APIs.

Only fixed provider base URLs and explicitly registered paths are callable.
No arbitrary URL tool is exposed. Credentials are read from the process
environment at invocation time and are never included in results or logs.
"""

import asyncio
import base64
import json
from email.message import EmailMessage
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
                "notion.page.create": HttpOperation("POST", "/pages", body_keys=("parent", "properties", "children", "icon", "cover")),
                "notion.page.update": HttpOperation("PATCH", "/pages/{page_id}", body_keys=("properties", "archived", "in_trash", "icon", "cover")),
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
        elif tool_name == "notion.page.update":
            page_id = str(arguments.get("page_id", "")).strip()
            if not page_id or any(ch not in "0123456789abcdefABCDEF-" for ch in page_id):
                raise ValueError("invalid_page_id")
            operation = HttpOperation("PATCH", f"/pages/{page_id}",
                body_keys=("properties", "archived", "in_trash", "icon", "cover"))
        return await self.invoke_operation(operation, arguments)

class GoogleWorkspaceAdapter:
    """Google Workspace REST adapter using OAuth refresh-token credentials."""

    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_ROOT = "https://www.googleapis.com"

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._expires_at = 0.0
        self.timeout = 20.0

    async def health_check(self) -> bool:
        return all(os.environ.get(key, "").strip() for key in (
            "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"
        ))

    async def _token(self) -> str:
        import time
        if not await self.health_check():
            raise RuntimeError("connector_credentials_missing")
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token
        data = urlencode({"client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "refresh_token": os.environ.get("GOOGLE_REFRESH_TOKEN", ""),
            "grant_type": "refresh_token"}).encode()
        request = Request(self.TOKEN_URL, data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        def refresh() -> dict:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc: raise RuntimeError(f"google_oauth_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("google_oauth_unreachable") from None
        payload = await asyncio.to_thread(refresh)
        token = payload.get("access_token")
        if not token: raise RuntimeError("google_oauth_token_missing")
        self._access_token = str(token)
        self._expires_at = time.time() + int(payload.get("expires_in", 3600))
        return self._access_token

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        token = await self._token()
        method, path, query, body = "GET", "", {}, None
        if tool_name == "gmail.search":
            path = "/gmail/v1/users/me/messages"
            query = {k: arguments[k] for k in ("q", "maxResults", "pageToken") if k in arguments}
        elif tool_name == "gmail.read":
            item = str(arguments.get("message_id", "")).strip()
            if not item or not all(ch.isalnum() or ch in "-_" for ch in item): raise ValueError("invalid_message_id")
            path, query = f"/gmail/v1/users/me/messages/{item}", {"format": "full"}
        elif tool_name in {"gmail.draft", "gmail.send"}:
            message = EmailMessage()
            message["To"], message["Subject"] = arguments["to"], arguments["subject"]
            message.set_content(arguments["body"])
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
            body, method = {"message": {"raw": raw}}, "POST"
            path = ("/gmail/v1/users/me/drafts" if tool_name == "gmail.draft"
                    else "/gmail/v1/users/me/messages/send")
        elif tool_name == "calendar.search":
            path = "/calendar/v3/calendars/primary/events"
            query = {k: arguments[k] for k in ("timeMin", "timeMax", "q", "maxResults", "pageToken") if k in arguments}
        elif tool_name == "calendar.create":
            method, path = "POST", "/calendar/v3/calendars/primary/events"
            body = {k: arguments[k] for k in ("summary", "description", "start", "end", "attendees") if k in arguments}
        elif tool_name == "calendar.update":
            item = str(arguments.get("event_id", "")).strip()
            if not item or not all(ch.isalnum() or ch in "-_" for ch in item): raise ValueError("invalid_event_id")
            method, path = "PATCH", f"/calendar/v3/calendars/primary/events/{item}"
            body = {k: arguments[k] for k in ("summary", "description", "start", "end", "attendees", "status") if k in arguments}
            if not body: raise ValueError("empty_event_update")
        elif tool_name == "drive.search":
            path = "/drive/v3/files"
            query = {k: arguments[k] for k in ("q", "pageSize", "orderBy", "fields", "pageToken") if k in arguments}
            query.setdefault("fields", "files(id,name,mimeType,webViewLink),nextPageToken")
        elif tool_name == "drive.upload":
            filename = str(arguments.get("file_name", "")).strip()
            mime_type = str(arguments.get("mime_type", "application/octet-stream")).strip()
            if not filename or len(filename) > 255 or "/" in filename or "\\\\" in filename:
                raise ValueError("invalid_drive_filename")
            try:
                binary = base64.b64decode(arguments["content_base64"], validate=True)
            except Exception:
                raise ValueError("invalid_base64_content") from None
            if len(binary) > 10 * 1024 * 1024:
                raise ValueError("drive_upload_exceeds_10mb_limit")
            metadata = {"name": filename}
            if arguments.get("parent_id"):
                metadata["parents"] = [arguments["parent_id"]]
            boundary = "rune-upload-boundary"
            payload = (
                f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n"
                + json.dumps(metadata)
                + f"\r\n--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n"
            ).encode() + binary + f"\r\n--{boundary}--".encode()
            query = {"uploadType": "multipart", "fields": "id,name,mimeType,webViewLink"}
            path = "/upload/drive/v3/files"
            method = "POST"
            body = None
            upload_payload = payload
        elif tool_name == "contacts.search":
            path = "/people/v1/people/me/connections"
            query = {k: arguments[k] for k in ("pageSize", "personFields", "pageToken") if k in arguments}
            query.setdefault("personFields", "names,emailAddresses,phoneNumbers")
        else: raise RuntimeError("tool_operation_not_implemented")
        url = self.API_ROOT + path + (("?" + urlencode(query, doseq=True)) if query else "")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        data = json.dumps(body).encode("utf-8") if body is not None else None
        if tool_name == "drive.upload":
            data = upload_payload
            headers["Content-Type"] = "multipart/related; boundary=rune-upload-boundary"
        elif data is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method)
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode("utf-8")) if raw else {}
            except HTTPError as exc: raise RuntimeError(f"google_api_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("google_api_unreachable") from None
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
                "figma.comment.create": HttpOperation("POST", "/files/{file_key}/comments", body_keys=("message", "client_meta")),
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



class ResendAdapter(JsonHttpAdapter):
    """Resend transactional email API adapter."""

    def __init__(self) -> None:
        super().__init__(
            base_url="https://api.resend.com",
            credential_env="RESEND_API_KEY",
            operations={
                "email.send": HttpOperation(
                    "POST", "/emails",
                    body_keys=("from", "to", "subject", "html", "text", "reply_to", "cc", "bcc", "tags"),
                ),
            },
        )



class TelegramBotAdapter:
    """Official Telegram Bot API adapter for authorised bot messaging."""

    def __init__(self) -> None:
        self.timeout = 20.0

    async def health_check(self) -> bool:
        return bool(os.environ.get("TELEGRAM_BOT_TOKEN", "").strip())

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name != "telegram.message.send":
            raise RuntimeError("tool_operation_not_implemented")
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("connector_credentials_missing")
        chat_id = str(arguments.get("chat_id", "")).strip()
        text_value = str(arguments.get("text", ""))
        if not chat_id or len(chat_id) > 128 or not text_value or len(text_value) > 4096:
            raise ValueError("invalid_telegram_message")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        body = {"chat_id": chat_id, "text": text_value}
        if "parse_mode" in arguments:
            body["parse_mode"] = arguments["parse_mode"]
        if "disable_notification" in arguments:
            body["disable_notification"] = arguments["disable_notification"]
        request = Request(url, data=json.dumps(body).encode("utf-8"),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST")
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    payload = json.loads(raw.decode("utf-8")) if raw else {}
                    if not payload.get("ok", False):
                        raise RuntimeError("telegram_api_rejected_request")
                    return payload.get("result", {})
            except HTTPError as exc:
                raise RuntimeError(f"telegram_api_http_{exc.code}") from None
            except (URLError, TimeoutError):
                raise RuntimeError("telegram_api_unreachable") from None
        return await asyncio.to_thread(send)



class GitHubAdapter(JsonHttpAdapter):
    """GitHub REST adapter for repository search, issue and pull-request creation."""

    def __init__(self) -> None:
        super().__init__(
            base_url="https://api.github.com",
            credential_env="GITHUB_TOKEN",
            fixed_headers={"X-GitHub-Api-Version": "2022-11-28"},
            operations={
                "github.repo.search": HttpOperation(
                    "GET", "/search/repositories",
                    query_keys=("q", "sort", "order", "per_page", "page"),
                ),
            },
        )

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        operation = self.operations.get(tool_name)
        if tool_name in {"github.issue.create", "github.pull_request.create"}:
            owner = str(arguments.get("owner", "")).strip()
            repo = str(arguments.get("repo", "")).strip()
            if (not owner or not repo or owner in {".", ".."} or repo in {".", ".."}
                    or any(not (part.replace("-", "").replace("_", "").replace(".", "").isalnum())
                           for part in (owner, repo))):
                raise ValueError("invalid_github_repository")
            if tool_name == "github.issue.create":
                operation = HttpOperation("POST", f"/repos/{owner}/{repo}/issues",
                    body_keys=("title", "body", "assignees", "labels", "milestone"))
            else:
                operation = HttpOperation("POST", f"/repos/{owner}/{repo}/pulls",
                    body_keys=("title", "head", "base", "body", "draft", "maintainer_can_modify"))
        if operation is None:
            raise RuntimeError("tool_operation_not_implemented")
        return await self.invoke_operation(operation, arguments)



class SlackAdapter(JsonHttpAdapter):
    """Slack Web API adapter with user-token search and bot-token messaging."""

    def __init__(self) -> None:
        super().__init__(
            base_url="https://slack.com/api",
            credential_env="SLACK_BOT_TOKEN",
            operations={},
        )

    async def health_check(self) -> bool:
        return bool(os.environ.get("SLACK_BOT_TOKEN", "").strip()
                    or os.environ.get("SLACK_USER_TOKEN", "").strip())

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name == "slack.search":
            token = os.environ.get("SLACK_USER_TOKEN", "").strip()
            if not token:
                raise RuntimeError("slack_user_token_required_for_search")
            operation = HttpOperation("GET", "/search.messages",
                query_keys=("query", "count", "page"))
        elif tool_name == "slack.message.send":
            token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
            if not token:
                raise RuntimeError("slack_bot_token_required_for_messaging")
            operation = HttpOperation("POST", "/chat.postMessage",
                body_keys=("channel", "text"))
        else:
            raise RuntimeError("tool_operation_not_implemented")
        query = {key: arguments[key] for key in operation.query_keys if key in arguments}
        body = {key: arguments[key] for key in operation.body_keys if key in arguments}
        url = self.base_url + operation.path
        if query:
            url += "?" + urlencode(query, doseq=True)
        data = json.dumps(body).encode() if operation.method != "GET" else None
        request = Request(url, data=data,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                     **({"Content-Type": "application/json"} if data is not None else {})},
            method=operation.method)
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    payload = json.loads(raw.decode()) if raw else {}
                    if isinstance(payload, dict) and payload.get("ok") is False:
                        raise RuntimeError("slack_api_rejected_request")
                    return payload
            except HTTPError as exc:
                raise RuntimeError(f"slack_api_http_{exc.code}") from None
            except (URLError, TimeoutError):
                raise RuntimeError("slack_unreachable") from None
        return await asyncio.to_thread(send)


class DiscordBotAdapter(JsonHttpAdapter):
    """Discord bot REST adapter. Uses bot tokens, never user-account tokens."""

    def __init__(self) -> None:
        super().__init__(
            base_url="https://discord.com/api/v10",
            credential_env="DISCORD_BOT_TOKEN",
            auth_scheme="Bot",
            operations={},
        )

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name != "discord.message.send":
            raise RuntimeError("tool_operation_not_implemented")
        channel_id = str(arguments.get("channel_id", "")).strip()
        content = str(arguments.get("content", ""))
        if not channel_id.isdigit() or not content or len(content) > 2000:
            raise ValueError("invalid_discord_message")
        operation = HttpOperation("POST", f"/channels/{channel_id}/messages",
            body_keys=("content",))
        return await self.invoke_operation(operation, arguments)



class DropboxAdapter:
    """Dropbox API adapter with refresh-token OAuth and bounded file operations."""

    TOKEN_URL = "https://api.dropbox.com/oauth2/token"
    API_ROOT = "https://api.dropboxapi.com/2"

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at = 0.0
        self.timeout = 25.0

    async def health_check(self) -> bool:
        return all(os.environ.get(k, "").strip() for k in (
            "DROPBOX_APP_KEY", "DROPBOX_APP_SECRET", "DROPBOX_REFRESH_TOKEN"))

    async def _access_token(self) -> str:
        import time
        if not await self.health_check():
            raise RuntimeError("connector_credentials_missing")
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        form = urlencode({
            "grant_type": "refresh_token",
            "refresh_token": os.environ["DROPBOX_REFRESH_TOKEN"],
            "client_id": os.environ["DROPBOX_APP_KEY"],
            "client_secret": os.environ["DROPBOX_APP_SECRET"],
        }).encode()
        request = Request(self.TOKEN_URL, data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        def refresh() -> dict:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc: raise RuntimeError(f"dropbox_oauth_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("dropbox_unreachable") from None
        payload = await asyncio.to_thread(refresh)
        if not payload.get("access_token"):
            raise RuntimeError("dropbox_token_missing")
        self._token = str(payload["access_token"])
        self._expires_at = time.time() + int(payload.get("expires_in", 14400))
        return self._token

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        token = await self._access_token()
        if tool_name == "dropbox.files.search":
            if arguments.get("cursor"):
                endpoint = "/files/search/continue_v2"
                body = {"cursor": arguments["cursor"]}
            else:
                endpoint = "/files/search_v2"
                body = {"query": arguments["query"]}
                if arguments.get("path"):
                    body["options"] = {"path": arguments["path"]}
            headers = {"Content-Type": "application/json"}
        elif tool_name == "drive.upload":
            # Google Drive upload belongs to GoogleWorkspaceAdapter, not Dropbox.
            raise RuntimeError("tool_operation_not_implemented")
        else:
            raise RuntimeError("tool_operation_not_implemented")
        request = Request(self.API_ROOT + endpoint, data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST")
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode()) if raw else {}
            except HTTPError as exc: raise RuntimeError(f"dropbox_api_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("dropbox_unreachable") from None
        return await asyncio.to_thread(send)



class SpotifyAdapter:
    """Spotify Web API adapter with refresh-token OAuth."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at = 0.0
        self.timeout = 20.0

    async def health_check(self) -> bool:
        return all(os.environ.get(k, "").strip() for k in (
            "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REFRESH_TOKEN"))

    async def _access_token(self) -> str:
        import time
        if not await self.health_check():
            raise RuntimeError("connector_credentials_missing")
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        raw = f"{os.environ['SPOTIFY_CLIENT_ID']}:{os.environ['SPOTIFY_CLIENT_SECRET']}".encode()
        auth = base64.b64encode(raw).decode()
        form = urlencode({"grant_type": "refresh_token",
            "refresh_token": os.environ["SPOTIFY_REFRESH_TOKEN"]}).encode()
        request = Request("https://accounts.spotify.com/api/token", data=form,
            headers={"Authorization": f"Basic {auth}",
                     "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        def refresh() -> dict:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode())
            except HTTPError as exc: raise RuntimeError(f"spotify_oauth_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("spotify_unreachable") from None
        payload = await asyncio.to_thread(refresh)
        if not payload.get("access_token"): raise RuntimeError("spotify_token_missing")
        self._token = str(payload["access_token"])
        self._expires_at = time.time() + int(payload.get("expires_in", 3600))
        return self._token

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        token = await self._access_token()
        if tool_name == "spotify.search":
            query = {"q": arguments["q"], "type": arguments.get("type", "track"),
                     "limit": arguments.get("limit", 10), "offset": arguments.get("offset", 0)}
            method, path, body = "GET", "/search?" + urlencode(query), None
        elif tool_name == "spotify.playback.start":
            query = {"device_id": arguments["device_id"]} if arguments.get("device_id") else {}
            path = "/me/player/play" + (("?" + urlencode(query)) if query else "")
            method, body = "PUT", {"context_uri": arguments["uri"]} if arguments["uri"].startswith("spotify:") else {"uris": [arguments["uri"]]}
        else: raise RuntimeError("tool_operation_not_implemented")
        request = Request("https://api.spotify.com/v1" + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                     **({"Content-Type": "application/json"} if body is not None else {})},
            method=method)
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode()) if raw else {"status": "accepted"}
            except HTTPError as exc: raise RuntimeError(f"spotify_api_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("spotify_unreachable") from None
        return await asyncio.to_thread(send)


class YouTubeAdapter(JsonHttpAdapter):
    """YouTube Data API v3 search adapter using a restricted API key."""

    def __init__(self) -> None:
        super().__init__(base_url="https://www.googleapis.com/youtube/v3",
            credential_env="YOUTUBE_API_KEY", auth_header="X-Goog-Api-Key",
            auth_scheme="", operations={
                "youtube.search": HttpOperation("GET", "/search",
                    query_keys=("q", "type", "maxResults", "part")),
            })

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name != "youtube.search":
            raise RuntimeError("tool_operation_not_implemented")
        # The API key is sent as a query parameter by this API.
        credential = self._credential()
        query = {k: arguments[k] for k in ("q", "type", "maxResults", "pageToken") if k in arguments}
        query.update({"part": "snippet", "key": credential})
        request = Request(self.base_url + "/search?" + urlencode(query),
            headers={"Accept": "application/json"}, method="GET")
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode()) if raw else {}
            except HTTPError as exc: raise RuntimeError(f"youtube_api_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("youtube_unreachable") from None
        return await asyncio.to_thread(send)


class ZoteroAdapter(JsonHttpAdapter):
    """Zotero Web API adapter for item search."""

    def __init__(self) -> None:
        super().__init__(base_url="https://api.zotero.org",
            credential_env="ZOTERO_API_KEY", auth_header="Zotero-API-Key",
            auth_scheme="", operations={
                "zotero.items.search": HttpOperation("GET", "/users/{user_id}/items",
                    query_keys=("q", "limit", "format")),
            })

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name != "zotero.items.search":
            raise RuntimeError("tool_operation_not_implemented")
        user_id = os.environ.get("ZOTERO_USER_ID", "").strip()
        if not user_id or not user_id.isdigit():
            raise RuntimeError("zotero_user_id_missing_or_invalid")
        credential = self._credential()
        query = {"q": arguments["q"], "limit": arguments.get("limit", 25),
                 "format": "json"}
        request = Request(f"https://api.zotero.org/users/{user_id}/items?" + urlencode(query),
            headers={"Zotero-API-Key": credential, "Accept": "application/json"})
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode()) if raw else []
            except HTTPError as exc: raise RuntimeError(f"zotero_api_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("zotero_unreachable") from None
        return await asyncio.to_thread(send)



class Microsoft365Adapter:
    """Microsoft Graph adapter for Outlook mail search using refresh-token OAuth."""

    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at = 0.0
        self.timeout = 20.0

    async def health_check(self) -> bool:
        return all(os.environ.get(k, "").strip() for k in (
            "MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET", "MICROSOFT_REFRESH_TOKEN"))

    async def _access_token(self) -> str:
        import time
        if not await self.health_check():
            raise RuntimeError("connector_credentials_missing")
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        form = urlencode({
            "client_id": os.environ["MICROSOFT_CLIENT_ID"],
            "client_secret": os.environ["MICROSOFT_CLIENT_SECRET"],
            "refresh_token": os.environ["MICROSOFT_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
            "scope": "offline_access https://graph.microsoft.com/Mail.Read",
        }).encode()
        request = Request(self.TOKEN_URL, data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        def refresh() -> dict:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode())
            except HTTPError as exc: raise RuntimeError(f"microsoft_oauth_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("microsoft_unreachable") from None
        payload = await asyncio.to_thread(refresh)
        if not payload.get("access_token"): raise RuntimeError("microsoft_token_missing")
        self._token = str(payload["access_token"])
        self._expires_at = time.time() + int(payload.get("expires_in", 3600))
        return self._token

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name != "outlook.search":
            raise RuntimeError("tool_operation_not_implemented")
        token = await self._access_token()
        query = {"$search": f'"{arguments["query"]}"',
                 "$top": arguments.get("top", 25),
                 "$select": "id,subject,from,receivedDateTime,bodyPreview"}
        request = Request(self.GRAPH_ROOT + "/me/messages?" + urlencode(query),
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                     "ConsistencyLevel": "eventual"})
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode()) if raw else {}
            except HTTPError as exc: raise RuntimeError(f"microsoft_graph_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("microsoft_graph_unreachable") from None
        return await asyncio.to_thread(send)



class HubSpotAdapter(JsonHttpAdapter):
    """HubSpot CRM search and deal update adapter."""

    def __init__(self) -> None:
        super().__init__(base_url="https://api.hubapi.com", credential_env="HUBSPOT_ACCESS_TOKEN",
            operations={
                "hubspot.contacts.search": HttpOperation("POST", "/crm/v3/objects/contacts/search",
                    body_keys=("query", "limit", "filterGroups", "properties", "sorts")),
            })

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name == "hubspot.deal.update":
            deal_id = str(arguments.get("deal_id", "")).strip()
            if not deal_id.isdigit(): raise ValueError("invalid_hubspot_deal_id")
            operation = HttpOperation("PATCH", f"/crm/v3/objects/deals/{deal_id}",
                body_keys=("properties",))
            return await self.invoke_operation(operation, arguments)
        if tool_name == "hubspot.contacts.search":
            operation = HttpOperation("POST", "/crm/v3/objects/contacts/search",
                body_keys=("query", "limit"))
            payload = {"query": arguments.get("q", ""), "limit": arguments.get("limit", 25)}
            return await self.invoke_operation(operation, payload)
        return await super().invoke(tool_name, arguments)


class SentryAdapter(JsonHttpAdapter):
    """Sentry issue search adapter."""

    def __init__(self) -> None:
        super().__init__(base_url="https://sentry.io/api/0", credential_env="SENTRY_AUTH_TOKEN",
            auth_scheme="Bearer", operations={
                "sentry.issues.search": HttpOperation("GET", "/issues/",
                    query_keys=("query", "project", "limit")),
            })


class VercelAdapter(JsonHttpAdapter):
    """Vercel deployment list and deployment creation adapter."""

    def __init__(self) -> None:
        super().__init__(base_url="https://api.vercel.com", credential_env="VERCEL_TOKEN",
            operations={
                "vercel.deployments.list": HttpOperation("GET", "/v6/deployments",
                    query_keys=("projectId", "limit")),
            })

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name == "vercel.production.deploy":
            project_id = str(arguments.get("projectId", "")).strip()
            name = str(arguments.get("name", "")).strip()
            if not project_id or not name or not arguments.get("gitSource"):
                raise ValueError("vercel_deploy_requires_project_name_and_git_source")
            operation = HttpOperation("POST", "/v13/deployments",
                body_keys=("name", "project", "target", "gitSource"))
            payload = dict(arguments)
            payload["project"] = project_id
            return await self.invoke_operation(operation, payload)
        return await super().invoke(tool_name, arguments)


class RailwayAdapter(JsonHttpAdapter):
    """Railway GraphQL adapter for deployment logs."""

    def __init__(self) -> None:
        super().__init__(base_url="https://backboard.railway.com/graphql/v2",
            credential_env="RAILWAY_API_TOKEN", operations={})

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name != "railway.logs.read":
            raise RuntimeError("tool_operation_not_implemented")
        deployment_id = str(arguments.get("deploymentId", "")).strip()
        if not deployment_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in deployment_id):
            raise ValueError("invalid_railway_deployment_id")
        lines = max(1, min(int(arguments.get("lines", 100)), 500))
        query = "query deploymentLogs($deploymentId: String!, $limit: Int) { deploymentLogs(deploymentId: $deploymentId, limit: $limit) { timestamp message severity } }"
        request = Request(self.base_url,
            data=json.dumps({"query": query, "variables": {"deploymentId": deployment_id, "limit": lines}}).encode(),
            headers={"Authorization": f"Bearer {self._credential()}",
                     "Content-Type": "application/json", "Accept": "application/json"},
            method="POST")
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    payload = json.loads(raw.decode()) if raw else {}
                    if payload.get("errors"): raise RuntimeError("railway_graphql_error")
                    return payload.get("data", {})
            except HTTPError as exc: raise RuntimeError(f"railway_api_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("railway_unreachable") from None
        return await asyncio.to_thread(send)



class MetaGraphAdapter:
    """Official Meta Graph adapter for eligible Instagram, Facebook and Threads APIs."""

    def __init__(self) -> None:
        self.timeout = 20.0

    def _version(self) -> str:
        version = os.environ.get("META_GRAPH_VERSION", "").strip()
        if not version or not version.startswith("v"):
            raise RuntimeError("meta_graph_version_must_be_configured")
        return version

    def _token(self) -> str:
        token = os.environ.get("META_ACCESS_TOKEN", "").strip()
        if not token: raise RuntimeError("connector_credentials_missing")
        return token

    async def health_check(self) -> bool:
        return bool(os.environ.get("META_ACCESS_TOKEN", "").strip()
                    and os.environ.get("META_GRAPH_VERSION", "").strip())

    async def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        query = {"access_token": self._token()} if method == "GET" else {}
        url = f"https://graph.facebook.com/{self._version()}{path}"
        if query: url += "?" + urlencode(query)
        payload = dict(body or {})
        if method != "GET": payload["access_token"] = self._token()
        request = Request(url, data=json.dumps(payload).encode() if method != "GET" else None,
            headers={"Accept": "application/json",
                     **({"Content-Type": "application/json"} if method != "GET" else {})},
            method=method)
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    result = json.loads(raw.decode()) if raw else {}
                    if isinstance(result, dict) and result.get("error"):
                        raise RuntimeError("meta_graph_api_rejected_request")
                    return result
            except HTTPError as exc: raise RuntimeError(f"meta_graph_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("meta_graph_unreachable") from None
        return await asyncio.to_thread(send)

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name == "facebook.page.publish":
            page_id = str(arguments["page_id"]).strip()
            if not page_id.isdigit(): raise ValueError("invalid_meta_page_id")
            body = {k: arguments[k] for k in ("message", "link") if k in arguments}
            return await self._request("POST", f"/{page_id}/feed", body)
        if tool_name == "instagram.comments.read":
            user_id, media_id = str(arguments["ig_user_id"]), str(arguments["media_id"])
            if not user_id.isdigit() or not media_id.isdigit(): raise ValueError("invalid_meta_object_id")
            return await self._request("GET", f"/{media_id}/comments")
        if tool_name == "instagram.media.publish":
            user_id = str(arguments["ig_user_id"]).strip()
            image_url = str(arguments["image_url"]).strip()
            if not user_id.isdigit() or not image_url.startswith("https://"):
                raise ValueError("invalid_instagram_publish_input")
            create = await self._request("POST", f"/{user_id}/media",
                {"image_url": image_url, "caption": arguments.get("caption", "")})
            creation_id = str(create.get("id", ""))
            if not creation_id: raise RuntimeError("meta_media_container_missing")
            return await self._request("POST", f"/{user_id}/media_publish",
                {"creation_id": creation_id})
        if tool_name == "threads.post.publish":
            user_id = str(arguments["user_id"]).strip()
            if not user_id.isdigit(): raise ValueError("invalid_threads_user_id")
            create = await self._request("POST", f"/{user_id}/threads",
                {"text": arguments["text"], **({"image_url": arguments["media_url"]} if arguments.get("media_url") else {})})
            creation_id = str(create.get("id", ""))
            if not creation_id: raise RuntimeError("meta_threads_container_missing")
            return await self._request("POST", f"/{user_id}/threads_publish",
                {"creation_id": creation_id})
        raise RuntimeError("tool_operation_not_implemented")



class XApiAdapter(JsonHttpAdapter):
    """X API v2 recent search and post creation using user-context access token."""

    def __init__(self) -> None:
        super().__init__(base_url="https://api.x.com/2", credential_env="X_ACCESS_TOKEN",
            operations={
                "x.search": HttpOperation("GET", "/tweets/search/recent",
                    query_keys=("query", "max_results")),
            })

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name == "x.post.create":
            text_value = str(arguments.get("text", ""))
            if not text_value or len(text_value) > 280:
                raise ValueError("invalid_x_post_text")
            body = {"text": text_value}
            if arguments.get("reply_to_id"):
                body["reply"] = {"in_reply_to_tweet_id": arguments["reply_to_id"]}
            operation = HttpOperation("POST", "/tweets", body_keys=("text", "reply"))
            return await self.invoke_operation(operation, body)
        return await super().invoke(tool_name, arguments)



class RedditAdapter:
    """Reddit OAuth adapter for search and authorised comment creation."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at = 0.0
        self.timeout = 20.0

    async def health_check(self) -> bool:
        return all(os.environ.get(k, "").strip() for k in (
            "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_REFRESH_TOKEN"))

    async def _access_token(self) -> str:
        import time
        if not await self.health_check(): raise RuntimeError("connector_credentials_missing")
        if self._token and time.time() < self._expires_at - 60: return self._token
        basic = base64.b64encode((os.environ["REDDIT_CLIENT_ID"] + ":" +
            os.environ["REDDIT_CLIENT_SECRET"]).encode()).decode()
        form = urlencode({"grant_type": "refresh_token",
            "refresh_token": os.environ["REDDIT_REFRESH_TOKEN"]}).encode()
        request = Request("https://www.reddit.com/api/v1/access_token", data=form,
            headers={"Authorization": f"Basic {basic}",
                     "Content-Type": "application/x-www-form-urlencoded",
                     "User-Agent": "RUNE/0.1 connector"}, method="POST")
        def refresh() -> dict:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode())
            except HTTPError as exc: raise RuntimeError(f"reddit_oauth_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("reddit_unreachable") from None
        payload = await asyncio.to_thread(refresh)
        if not payload.get("access_token"): raise RuntimeError("reddit_token_missing")
        self._token = str(payload["access_token"])
        self._expires_at = time.time() + int(payload.get("expires_in", 3600))
        return self._token

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        token = await self._access_token()
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "RUNE/0.1 connector",
                   "Accept": "application/json"}
        if tool_name == "reddit.search":
            query = {"q": arguments["query"], "limit": min(int(arguments.get("limit", 25)), 100),
                     "sort": arguments.get("sort", "relevance"),
                     **({"after": arguments["after"]} if arguments.get("after") else {}),
                     **({"before": arguments["before"]} if arguments.get("before") else {})}
            path = "/search.json?" + urlencode(query)
            request = Request("https://oauth.reddit.com" + path, headers=headers)
        elif tool_name == "reddit.comment.create":
            parent = str(arguments["parent_id"]).strip()
            text_value = str(arguments["text"])
            if not parent.startswith(("t1_", "t3_")) or not text_value or len(text_value) > 10000:
                raise ValueError("invalid_reddit_comment")
            data = urlencode({"thing_id": parent, "text": text_value}).encode()
            request = Request("https://oauth.reddit.com/api/comment", data=data,
                headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
                method="POST")
        else: raise RuntimeError("tool_operation_not_implemented")
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode()) if raw else {}
            except HTTPError as exc: raise RuntimeError(f"reddit_api_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("reddit_unreachable") from None
        return await asyncio.to_thread(send)


class PinterestAdapter(JsonHttpAdapter):
    """Pinterest API v5 pin creation."""

    def __init__(self) -> None:
        super().__init__(base_url="https://api.pinterest.com/v5",
            credential_env="PINTEREST_ACCESS_TOKEN", operations={
                "pinterest.pin.create": HttpOperation("POST", "/pins",
                    body_keys=("board_id", "title", "description", "link", "media_source")),
            })



class WhatsAppBusinessAdapter(JsonHttpAdapter):
    """WhatsApp Cloud API adapter for opt-in business messaging only."""

    def __init__(self) -> None:
        super().__init__(base_url="https://graph.facebook.com",
            credential_env="WHATSAPP_ACCESS_TOKEN", operations={})
        from ..core.messaging_consent import MessagingConsentRegistry
        self.consent = MessagingConsentRegistry(os.environ.get("RUNE_CONSENT_DB"))

    async def health_check(self) -> bool:
        return bool(await super().health_check() and
                    os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip().isdigit() and
                    os.environ.get("WHATSAPP_API_VERSION", "").strip().startswith("v"))

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name != "whatsapp.message.send":
            raise RuntimeError("tool_operation_not_implemented")
        version = os.environ.get("WHATSAPP_API_VERSION", "").strip()
        phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
        if not version.startswith("v") or not phone_id.isdigit():
            raise RuntimeError("whatsapp_api_version_or_phone_id_missing")
        recipient = str(arguments.get("to", "")).strip()
        message_type = str(arguments.get("type", "")).strip()
        if not recipient or len(recipient) > 32 or not recipient.replace("+", "").isdigit():
            raise ValueError("invalid_whatsapp_recipient")
        if not self.consent.can_send("whatsapp", recipient, message_type):
            raise RuntimeError("whatsapp_recipient_consent_or_window_required")
        if message_type == "text":
            text_body = arguments.get("text")
            if not isinstance(text_body, dict) or not text_body.get("body"):
                raise ValueError("whatsapp_text_body_required")
            message = {"messaging_product": "whatsapp", "to": recipient,
                       "type": "text", "text": {"body": str(text_body["body"])[:4096]}}
        elif message_type == "template":
            template = arguments.get("template")
            if not isinstance(template, dict) or not template.get("name") or not template.get("language"):
                raise ValueError("whatsapp_template_name_and_language_required")
            message = {"messaging_product": "whatsapp", "to": recipient,
                       "type": "template", "template": template}
        else:
            raise ValueError("whatsapp_message_type_must_be_text_or_template")
        request = Request(f"https://graph.facebook.com/{version}/{phone_id}/messages",
            data=json.dumps(message).encode(),
            headers={"Authorization": f"Bearer {self._credential()}",
                     "Content-Type": "application/json", "Accept": "application/json"},
            method="POST")
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode()) if raw else {}
            except HTTPError as exc: raise RuntimeError(f"whatsapp_api_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("whatsapp_unreachable") from None
        return await asyncio.to_thread(send)


class LinkedInAdapter(JsonHttpAdapter):
    """LinkedIn Posts API adapter; requires approved Community Management access."""

    def __init__(self) -> None:
        super().__init__(base_url="https://api.linkedin.com/rest",
            credential_env="LINKEDIN_ACCESS_TOKEN", operations={})

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name != "linkedin.post.create":
            raise RuntimeError("tool_operation_not_implemented")
        version = os.environ.get("LINKEDIN_API_VERSION", "").strip()
        author = str(arguments.get("author", "")).strip()
        commentary = str(arguments.get("commentary", ""))
        if not version.isdigit() or len(version) != 6:
            raise RuntimeError("linkedin_api_version_missing_or_invalid")
        if not author.startswith("urn:li:") or not commentary:
            raise ValueError("invalid_linkedin_post")
        body = {"author": author, "commentary": commentary,
                "visibility": arguments.get("visibility", "PUBLIC"),
                "distribution": {"feedDistribution": "MAIN_FEED",
                                 "targetEntities": [], "thirdPartyDistributionChannels": []},
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False}
        request = Request(self.base_url + "/posts", data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self._credential()}",
                     "Linkedin-Version": version,
                     "X-Restli-Protocol-Version": "2.0.0",
                     "Content-Type": "application/json", "Accept": "application/json"},
            method="POST")
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return {"status": response.status,
                            "post_id": response.headers.get("x-restli-id")}
            except HTTPError as exc: raise RuntimeError(f"linkedin_api_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("linkedin_unreachable") from None
        return await asyncio.to_thread(send)


class TikTokContentAdapter(JsonHttpAdapter):
    """TikTok Content Posting API URL-pull publishing for approved apps."""

    def __init__(self) -> None:
        super().__init__(base_url="https://open.tiktokapis.com/v2",
            credential_env="TIKTOK_ACCESS_TOKEN", operations={})

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name != "tiktok.content.publish":
            raise RuntimeError("tool_operation_not_implemented")
        video_url = str(arguments.get("video_url", "")).strip()
        title = str(arguments.get("title", ""))
        privacy = str(arguments.get("privacy_level", ""))
        if not video_url.startswith("https://") or not title or privacy not in {
            "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY"
        }:
            raise ValueError("invalid_tiktok_publish_arguments")
        body = {"post_info": {"title": title[:2200], "privacy_level": privacy},
                "source_info": {"source": "PULL_FROM_URL", "video_url": video_url}}
        request = Request(self.base_url + "/post/publish/video/init/",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self._credential()}",
                     "Content-Type": "application/json; charset=UTF-8",
                     "Accept": "application/json"},
            method="POST")
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode()) if raw else {}
            except HTTPError as exc: raise RuntimeError(f"tiktok_api_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("tiktok_unreachable") from None
        return await asyncio.to_thread(send)



class GitLabAdapter(JsonHttpAdapter):
    """GitLab REST adapter for project search, issue and merge-request creation."""

    def __init__(self) -> None:
        super().__init__(base_url=os.environ.get("GITLAB_API_URL") or "https://gitlab.com/api/v4",
            credential_env="GITLAB_TOKEN", auth_header="PRIVATE-TOKEN", auth_scheme="",
            operations={
                "gitlab.project.search": HttpOperation("GET", "/projects",
                    query_keys=("search", "per_page", "page", "membership")),
            })

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name in {"gitlab.issue.create", "gitlab.merge_request.create"}:
            project_id = arguments.get("project_id")
            if not isinstance(project_id, int) or project_id <= 0:
                raise ValueError("invalid_gitlab_project_id")
            if tool_name == "gitlab.issue.create":
                operation = HttpOperation("POST", f"/projects/{project_id}/issues",
                    body_keys=("title", "description", "labels"))
            else:
                operation = HttpOperation("POST", f"/projects/{project_id}/merge_requests",
                    body_keys=("source_branch", "target_branch", "title", "description"))
            return await self.invoke_operation(operation, arguments)
        return await super().invoke(tool_name, arguments)


class LinearAdapter:
    """Linear GraphQL adapter for issue search and creation."""

    def __init__(self) -> None:
        self.timeout = 20.0
        self.endpoint = "https://api.linear.app/graphql"

    async def health_check(self) -> bool:
        return bool(os.environ.get("LINEAR_API_KEY", "").strip())

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        token = os.environ.get("LINEAR_API_KEY", "").strip()
        if not token: raise RuntimeError("connector_credentials_missing")
        if tool_name == "linear.issue.search":
            query = "query IssueSearch($query: String!) { issues(filter: { title: { containsIgnoreCase: $query } }) { nodes { id identifier title url state { name } } } }"
            variables = {"query": arguments["query"]}
        elif tool_name == "linear.issue.create":
            query = "mutation IssueCreate($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { id identifier url } } }"
            variables = {"input": {"teamId": arguments["team_id"], "title": arguments["title"],
                **({"description": arguments["description"]} if arguments.get("description") else {}),
                **({"assigneeId": arguments["assignee_id"]} if arguments.get("assignee_id") else {})}}
        else: raise RuntimeError("tool_operation_not_implemented")
        request = Request(self.endpoint, data=json.dumps({"query": query, "variables": variables}).encode(),
            headers={"Authorization": token, "Content-Type": "application/json", "Accept": "application/json"},
            method="POST")
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    payload = json.loads(raw.decode()) if raw else {}
                    if payload.get("errors"): raise RuntimeError("linear_graphql_error")
                    return payload.get("data", {})
            except HTTPError as exc: raise RuntimeError(f"linear_api_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("linear_unreachable") from None
        return await asyncio.to_thread(send)

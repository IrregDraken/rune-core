from __future__ import annotations

"""Local adapters with explicit workspace and service boundaries."""

import asyncio
import ipaddress
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class ScopedFilesystemAdapter:
    """Read/write/delete only within a configured workspace root."""

    def __init__(self, root: str | None = None, max_bytes: int = 10 * 1024 * 1024) -> None:
        self.root = Path(root or os.environ.get("RUNE_WORKSPACE_DIR", "./workspace")).expanduser().resolve()
        self.max_bytes = max_bytes

    async def health_check(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            return self.root.is_dir()
        except OSError:
            return False

    def _path(self, value: str) -> Path:
        if not value or "\x00" in value:
            raise ValueError("invalid_workspace_path")
        candidate = (self.root / value).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            raise ValueError("workspace_path_outside_root") from None
        return candidate

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        path = self._path(str(arguments.get("path", "")))
        if tool_name == "filesystem.file.read":
            def read() -> str:
                if not path.is_file(): raise FileNotFoundError("workspace_file_not_found")
                data = path.read_bytes()
                if len(data) > self.max_bytes: raise ValueError("workspace_file_too_large")
                return data.decode("utf-8")
            return await asyncio.to_thread(read)
        if tool_name == "filesystem.file.write":
            content = str(arguments.get("content", ""))
            data = content.encode("utf-8")
            if len(data) > self.max_bytes: raise ValueError("workspace_file_too_large")
            def write() -> dict[str, Any]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                return {"path": str(path.relative_to(self.root)), "bytes_written": len(data)}
            return await asyncio.to_thread(write)
        if tool_name == "filesystem.file.delete":
            def delete() -> dict[str, Any]:
                if not path.is_file(): raise FileNotFoundError("workspace_file_not_found")
                path.unlink()
                return {"deleted": True, "path": str(path.relative_to(self.root))}
            return await asyncio.to_thread(delete)
        raise RuntimeError("tool_operation_not_implemented")


class HomeAssistantAdapter:
    """Home Assistant REST adapter; URL must be explicitly configured."""

    def __init__(self) -> None:
        self.timeout = 15.0

    def _base_url(self) -> str:
        value = os.environ.get("HOME_ASSISTANT_URL", "").strip().rstrip("/")
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError("home_assistant_url_missing_or_invalid")
        if parsed.username or parsed.password:
            raise RuntimeError("home_assistant_url_must_not_contain_credentials")
        return value

    async def health_check(self) -> bool:
        return bool(os.environ.get("HOME_ASSISTANT_TOKEN", "").strip()
                    and os.environ.get("HOME_ASSISTANT_URL", "").strip())

    async def invoke(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        base = self._base_url()
        if tool_name == "home_assistant.entity.read":
            entity = str(arguments.get("entity_id", "")).strip()
            if "." not in entity or any(ch in entity for ch in "/?#"): raise ValueError("invalid_entity_id")
            method, path, body = "GET", f"/api/states/{entity}", None
        elif tool_name == "home_assistant.service.call":
            domain = str(arguments.get("domain", "")).strip()
            service = str(arguments.get("service", "")).strip()
            entity = str(arguments.get("entity_id", "")).strip()
            if not all(x and x.replace("_", "").isalnum() for x in (domain, service)):
                raise ValueError("invalid_home_assistant_service")
            if "." not in entity or any(ch in entity for ch in "/?#"): raise ValueError("invalid_entity_id")
            method, path = "POST", f"/api/services/{domain}/{service}"
            body = {**arguments.get("service_data", {}), "entity_id": entity}
        else:
            raise RuntimeError("tool_operation_not_implemented")
        token = os.environ.get("HOME_ASSISTANT_TOKEN", "").strip()
        if not token: raise RuntimeError("connector_credentials_missing")
        request = Request(base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                     **({"Content-Type": "application/json"} if body is not None else {})},
            method=method)
        def send() -> Any:
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    return json.loads(raw.decode()) if raw else {}
            except HTTPError as exc: raise RuntimeError(f"home_assistant_http_{exc.code}") from None
            except (URLError, TimeoutError): raise RuntimeError("home_assistant_unreachable") from None
        return await asyncio.to_thread(send)

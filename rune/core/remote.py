from __future__ import annotations

import os
from urllib.parse import urlparse
from typing import Any
from uuid import UUID

import httpx


class RemoteBackendError(RuntimeError):
    pass


class RemoteBackendClient:
    """Owner-side client for the RUNE remote control plane.

    Owner access tokens remain in the trusted RUNE server process. They are
    never sent to device nodes or included in model prompts.
    """

    def __init__(
        self,
        base_url: str | None = None,
        access_token: str | None = None,
        *,
        timeout: float = 12.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("RUNE_REMOTE_BACKEND_URL", "")).rstrip("/")
        self.access_token = access_token or os.getenv("RUNE_OWNER_ACCESS_TOKEN", "")
        self.timeout = timeout
        self.transport = transport
        if not self.base_url:
            raise ValueError("RUNE_REMOTE_BACKEND_URL is required")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError("RUNE remote backend must use HTTPS outside localhost development")
        if not self.access_token:
            raise ValueError("RUNE_OWNER_ACCESS_TOKEN is required")

    def _request(self, method: str, path: str, *, body: dict[str, Any] | None = None) -> Any:
        headers = {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.request(method, f"{self.base_url}/v1{path}",
                                          headers=headers, json=body)
                response.raise_for_status()
                return response.json() if response.content else None
        except httpx.HTTPStatusError as exc:
            raise RemoteBackendError(f"remote backend rejected request ({exc.response.status_code})") from exc
        except httpx.HTTPError as exc:
            raise RemoteBackendError("remote backend is unreachable") from exc

    def register_device(
        self, device_name: str, platform: str, capabilities: list[str],
        *, app_version: str = "unknown", public_key: str | None = None,
    ) -> dict[str, Any]:
        return self._request("POST", "/devices/register", body={
            "device_name": device_name, "platform": platform,
            "app_version": app_version, "capabilities": capabilities,
            "public_key": public_key,
        })

    def list_devices(self) -> list[dict[str, Any]]:
        return self._request("GET", "/devices")

    def create_task(
        self, device_id: UUID | str, capability: str, arguments: dict[str, Any],
        *, expires_in_seconds: int = 60,
    ) -> dict[str, Any]:
        return self._request("POST", "/tasks", body={
            "device_id": str(device_id), "capability": capability,
            "arguments": arguments, "expires_in_seconds": expires_in_seconds,
            "requires_approval": True,
        })

    def approve_task(self, task_id: UUID | str) -> dict[str, Any]:
        return self._request("POST", f"/tasks/{task_id}/approve", body={})

    def task_status(self, task_id: UUID | str) -> dict[str, Any]:
        return self._request("GET", f"/tasks/{task_id}")

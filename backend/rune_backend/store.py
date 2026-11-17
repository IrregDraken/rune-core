from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from rune_backend.config import get_settings


class StoreError(RuntimeError):
    pass


class SupabaseStore:
    """Server-only PostgREST access. The secret key never leaves this process."""

    def _config(self) -> tuple[str, str]:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_secret_key:
            raise StoreError("server database credentials are not configured")
        return settings.supabase_url.rstrip("/"), settings.supabase_secret_key

    async def rpc(self, function: str, *, body: dict[str, Any] | None = None) -> Any:
        if not function.replace("_", "").isalnum():
            raise ValueError("invalid RPC function name")
        base_url, secret = self._config()
        headers = {
            "apikey": secret,
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{base_url}/rest/v1/rpc/{function}",
                    headers=headers,
                    json=body or {},
                )
        except httpx.HTTPError as exc:
            raise StoreError("database RPC request failed") from exc
        if response.is_error:
            raise StoreError(f"database RPC request failed ({response.status_code})")
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise StoreError("database returned an invalid response") from exc

    async def request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        prefer: str | None = None,
    ) -> Any:
        base_url, secret = self._config()
        headers = {
            "apikey": secret,
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method,
                    f"{base_url}/rest/v1/{table}",
                    headers=headers,
                    params=params,
                    json=body,
                )
        except httpx.HTTPError as exc:
            raise StoreError("database request failed") from exc
        if response.is_error:
            # Do not echo database response bodies; they can contain internals.
            raise StoreError(f"database request failed ({response.status_code})")
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise StoreError("database returned an invalid response") from exc


store = SupabaseStore()


def owner_filter(owner_id: UUID) -> dict[str, str]:
    return {"owner_id": f"eq.{owner_id}"}

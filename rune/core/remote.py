from __future__ import annotations

import base64
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class RemoteBackendError(RuntimeError):
    pass


class OwnerSession:
    """Refreshable Supabase owner session with encrypted refresh-token persistence."""

    def __init__(
        self,
        *,
        supabase_url: str,
        publishable_key: str,
        access_token: str = "",
        refresh_token: str = "",
        expires_at: int = 0,
        store_path: str = "data/rune-owner-session.db",
        encryption_key: bytes | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.publishable_key = publishable_key
        self.access_token = access_token
        self.expires_at = expires_at
        self.transport = transport
        self._lock = threading.Lock()
        self._aes = AESGCM(encryption_key) if encryption_key else None
        if refresh_token and self._aes is None:
            raise ValueError("an encryption key (RUNE_OWNER_TOKEN_ENCRYPTION_KEY) is required to persist refresh tokens")
        Path(store_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(store_path, check_same_thread=False)
        self._db.execute(
            "create table if not exists owner_session (id integer primary key check(id=1), nonce blob not null, ciphertext blob not null)"
        )
        self._db.commit()
        stored = self._db.execute("select 1 from owner_session where id=1").fetchone()
        if refresh_token and not stored:
            self._save_refresh_token(refresh_token)
        self.refresh_token = self._load_refresh_token()

    @classmethod
    def from_env(cls) -> "OwnerSession":
        key_text = os.getenv("RUNE_OWNER_TOKEN_ENCRYPTION_KEY", "")
        key = None
        if key_text:
            padded = key_text + "=" * (-len(key_text) % 4)
            try:
                key = base64.urlsafe_b64decode(padded)
            except Exception as exc:
                raise ValueError("owner token encryption key must be URL-safe base64") from exc
            if len(key) != 32:
                raise ValueError("owner token encryption key must decode to exactly 32 bytes")
        return cls(
            supabase_url=os.getenv("RUNE_SUPABASE_URL", ""),
            publishable_key=os.getenv("RUNE_SUPABASE_PUBLISHABLE_KEY", ""),
            access_token=os.getenv("RUNE_OWNER_ACCESS_TOKEN", ""),
            refresh_token=os.getenv("RUNE_OWNER_REFRESH_TOKEN", ""),
            expires_at=int(os.getenv("RUNE_OWNER_ACCESS_TOKEN_EXPIRES_AT", "0")),
            store_path=os.getenv("RUNE_OWNER_SESSION_DB", "data/rune-owner-session.db"),
            encryption_key=key,
        )

    def _save_refresh_token(self, token: str) -> None:
        if self._aes is None:
            raise ValueError("owner token encryption is not configured")
        nonce = os.urandom(12)
        ciphertext = self._aes.encrypt(nonce, token.encode("utf-8"), b"rune-owner-refresh-v1")
        self._db.execute(
            "insert into owner_session(id,nonce,ciphertext) values(1,?,?) "
            "on conflict(id) do update set nonce=excluded.nonce,ciphertext=excluded.ciphertext",
            (nonce, ciphertext),
        )
        self._db.commit()

    def _load_refresh_token(self) -> str:
        row = self._db.execute(
            "select nonce,ciphertext from owner_session where id=1"
        ).fetchone()
        if not row:
            return ""
        if self._aes is None:
            raise ValueError("encrypted owner refresh token exists but encryption key is missing")
        try:
            return self._aes.decrypt(row[0], row[1], b"rune-owner-refresh-v1").decode("utf-8")
        except Exception as exc:
            raise ValueError("could not decrypt stored owner refresh token") from exc

    def get_access_token(self) -> str:
        with self._lock:
            if self.access_token and self.expires_at > int(time.time()) + 60:
                return self.access_token
            if not self.refresh_token:
                if self.access_token:
                    raise RemoteBackendError("owner access token expired; refresh token is not configured")
                raise RemoteBackendError("owner session is not configured")
            if not self.supabase_url or not self.publishable_key:
                raise RemoteBackendError("Supabase owner-session configuration is incomplete")
            try:
                with httpx.Client(timeout=12.0, transport=self.transport) as client:
                    response = client.post(
                        f"{self.supabase_url}/auth/v1/token?grant_type=refresh_token",
                        headers={"apikey": self.publishable_key},
                        json={"refresh_token": self.refresh_token},
                    )
                    response.raise_for_status()
                    payload = response.json()
                self.access_token = str(payload["access_token"])
                self.refresh_token = str(payload["refresh_token"])
                self.expires_at = int(time.time()) + int(payload.get("expires_in", 3600))
                self._save_refresh_token(self.refresh_token)
                return self.access_token
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                raise RemoteBackendError("could not refresh Supabase owner session") from exc

    def close(self) -> None:
        self._db.close()


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
        session: OwnerSession | None = None,
        timeout: float = 12.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("RUNE_REMOTE_BACKEND_URL", "")).rstrip("/")
        self.access_token = access_token or ""
        self.session = session
        self.timeout = timeout
        self.transport = transport
        if not self.base_url:
            raise ValueError("RUNE_REMOTE_BACKEND_URL is required")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise ValueError("RUNE remote backend must use HTTPS outside localhost development")
        if self.session is None and access_token is None:
            if any(os.getenv(name) for name in (
                "RUNE_OWNER_ACCESS_TOKEN",
                "RUNE_OWNER_REFRESH_TOKEN",
                "RUNE_OWNER_TOKEN_ENCRYPTION_KEY",
            )):
                self.session = OwnerSession.from_env()
            else:
                raise ValueError("Configure a Supabase owner access token or encrypted refresh session for RUNE")
        if not self.access_token and self.session is None:
            raise ValueError("RUNE owner session is not configured")

    def _request(self, method: str, path: str, *, body: dict[str, Any] | None = None) -> Any:
        token = self.session.get_access_token() if self.session else self.access_token
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
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

    def current_owner(self) -> dict[str, Any]:
        """Return the owner identity validated by Supabase Auth in the control plane."""
        payload = self._request("GET", "/me")
        if not isinstance(payload, dict) or not payload.get("owner_id"):
            raise RemoteBackendError("control plane returned an invalid owner identity")
        return payload

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

    def close(self) -> None:
        if self.session:
            self.session.close()

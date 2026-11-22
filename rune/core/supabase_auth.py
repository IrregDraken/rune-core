from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SupabaseAuthConfigurationError(RuntimeError):
    """Raised when the API is exposed without Supabase Auth configuration."""


class SupabaseAuthVerifier:
    """Validate access tokens against Supabase Auth's authoritative /user endpoint.

    The API deliberately does not trust decoded JWT claims or user-editable
    metadata for authorization. A successful response from Auth establishes
    the current user identity for this request.
    """

    def __init__(
        self,
        project_url: str | None = None,
        publishable_key: str | None = None,
        *,
        timeout: float = 5.0,
        opener: Any = urlopen,
    ) -> None:
        self.project_url = (project_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.publishable_key = (
            publishable_key
            or os.getenv("SUPABASE_PUBLISHABLE_KEY")
            or os.getenv("SUPABASE_ANON_KEY", "")
        )
        self.timeout = timeout
        self.opener = opener

    @property
    def configured(self) -> bool:
        return bool(self.project_url and self.publishable_key)

    def verify(self, access_token: str | None) -> dict[str, Any] | None:
        if not self.configured:
            raise SupabaseAuthConfigurationError(
                "Supabase Auth is not configured; private API access is disabled."
            )
        if not access_token or len(access_token) > 16_384:
            return None

        request = Request(
            f"{self.project_url}/auth/v1/user",
            headers={
                "apikey": self.publishable_key,
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                if response.status != 200:
                    return None
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError:
            return None
        except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            # Fail closed. Do not turn an Auth outage into anonymous access.
            return None

        if not isinstance(payload, dict):
            return None
        subject = payload.get("id")
        if not isinstance(subject, str) or not subject:
            return None
        return {
            "id": subject,
            "email": payload.get("email") if isinstance(payload.get("email"), str) else None,
        }

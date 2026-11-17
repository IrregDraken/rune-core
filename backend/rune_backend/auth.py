from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from rune_backend.config import get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Owner:
    id: UUID
    email: str | None = None


async def require_owner(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Owner:
    settings = get_settings()
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Supabase Auth is not configured")

    # Ask Supabase Auth to validate the access token. Never trust a decoded JWT
    # payload without signature and claim verification.
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": settings.supabase_publishable_key,
                    "Authorization": f"Bearer {credentials.credentials}",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Identity provider unavailable") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Identity provider returned an invalid response") from exc
    try:
        owner_id = UUID(payload["id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Identity response is invalid") from exc
    return Owner(id=owner_id, email=payload.get("email"))

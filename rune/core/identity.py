from __future__ import annotations

import getpass
import hashlib
import secrets
import platform
import socket
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class IdentityAssurance(str, Enum):
    """Named assurance levels for owner identity evidence."""

    OBSERVED = "observed"
    VERIFIED = "verified"


@dataclass(frozen=True)
class OwnerIdentity:
    subject: str
    display_name: str
    device_id: str
    platform: str
    assurance: str = IdentityAssurance.OBSERVED


class IdentityProvider(Protocol):
    def current(self) -> OwnerIdentity: ...


class LocalIdentityProvider:
    """Derive a stable local identity from the current OS account and node.

    This is an identity *observation*, not biometric authentication. A future
    Windows Hello/passkey/speaker-verification adapter can upgrade assurance.
    """

    def current(self) -> OwnerIdentity:
        username = getpass.getuser()
        hostname = socket.gethostname()
        system = platform.system().lower()
        raw = f"{system}:{hostname}:{username}".encode("utf-8", "strict")
        device_id = hashlib.sha256(raw).hexdigest()[:32]
        return OwnerIdentity(
            subject=username,
            display_name=username,
            device_id=device_id,
            platform=system,
            assurance=IdentityAssurance.OBSERVED,
        )


class IdentityVerifier:
    """Separates observed identity from proof of authority."""

    def __init__(self, owner: OwnerIdentity) -> None:
        self.owner = owner

    def verify_session(
        self,
        *,
        presented_token: str | None,
        expected_token: str | None,
        presented_subject: str | None = None,
    ) -> bool:
        if not presented_token or not expected_token:
            return False
        if not secrets.compare_digest(presented_token, expected_token):
            return False
        if presented_subject is not None and presented_subject != self.owner.subject:
            return False
        return True


class ControlPlaneIdentityProvider:
    """Owner identity backed by a Supabase-authenticated RUNE control plane.

    Device attributes remain locally observed; owner subject/email are accepted
    only from the control plane's validated /v1/me response.
    """

    def __init__(self, remote_client, local: IdentityProvider | None = None) -> None:
        self.remote_client = remote_client
        self.local = local or LocalIdentityProvider()

    def current(self) -> OwnerIdentity:
        local = self.local.current()
        owner = self.remote_client.current_owner()
        return OwnerIdentity(
            subject=str(owner["owner_id"]),
            display_name=str(owner.get("email") or "RUNE owner"),
            device_id=local.device_id,
            platform=local.platform,
            assurance=IdentityAssurance.VERIFIED,
        )

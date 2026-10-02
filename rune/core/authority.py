from __future__ import annotations

import secrets
from dataclasses import dataclass


@dataclass
class Authority:
    """Short-lived local-session authority for privileged node actions."""

    token: str | None = None

    @classmethod
    def create(cls) -> "Authority":
        return cls(token=secrets.token_urlsafe(32))

    def accepts(self, presented: str | None) -> bool:
        return bool(self.token and presented and secrets.compare_digest(self.token, presented))

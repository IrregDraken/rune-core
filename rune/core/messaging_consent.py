from __future__ import annotations

"""Durable, fail-closed consent ledger for outbound messaging."""

import sqlite3
import time
from pathlib import Path


class MessagingConsentRegistry:
    def __init__(self, database_path: str | None = None) -> None:
        configured = database_path or "~/.rune/consent.sqlite3"
        self.path = Path(configured).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS messaging_consent (
                    channel TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    opted_in INTEGER NOT NULL DEFAULT 0,
                    source TEXT,
                    recorded_at REAL NOT NULL,
                    last_inbound_at REAL,
                    PRIMARY KEY (channel, recipient)
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @staticmethod
    def _recipient(value: str) -> str:
        normalized = "".join(ch for ch in str(value) if ch.isdigit())
        if not normalized or len(normalized) < 7 or len(normalized) > 15:
            raise ValueError("invalid_messaging_recipient")
        return normalized

    def record_opt_in(self, channel: str, recipient: str, source: str) -> None:
        key = self._recipient(recipient)
        if not channel.strip() or not source.strip():
            raise ValueError("consent_channel_and_source_required")
        now = time.time()
        with self._connect() as db:
            db.execute("""
                INSERT INTO messaging_consent
                    (channel, recipient, opted_in, source, recorded_at)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(channel, recipient) DO UPDATE SET
                    opted_in=1, source=excluded.source, recorded_at=excluded.recorded_at
            """, (channel.strip().lower(), key, source.strip()[:256], now))

    def revoke(self, channel: str, recipient: str, source: str) -> None:
        key = self._recipient(recipient)
        now = time.time()
        with self._connect() as db:
            db.execute("""
                INSERT INTO messaging_consent
                    (channel, recipient, opted_in, source, recorded_at)
                VALUES (?, ?, 0, ?, ?)
                ON CONFLICT(channel, recipient) DO UPDATE SET
                    opted_in=0, source=excluded.source, recorded_at=excluded.recorded_at
            """, (channel.strip().lower(), key, source.strip()[:256], now))

    def record_inbound(self, channel: str, recipient: str, timestamp: float | None = None) -> None:
        key = self._recipient(recipient)
        now = timestamp if timestamp is not None else time.time()
        with self._connect() as db:
            db.execute("""
                INSERT INTO messaging_consent
                    (channel, recipient, opted_in, recorded_at, last_inbound_at)
                VALUES (?, ?, 0, ?, ?)
                ON CONFLICT(channel, recipient) DO UPDATE SET
                    last_inbound_at=excluded.last_inbound_at
            """, (channel.strip().lower(), key, time.time(), now))

    def can_send(self, channel: str, recipient: str, message_type: str,
                 now: float | None = None) -> bool:
        key = self._recipient(recipient)
        with self._connect() as db:
            row = db.execute("""
                SELECT opted_in, last_inbound_at
                FROM messaging_consent WHERE channel=? AND recipient=?
            """, (channel.strip().lower(), key)).fetchone()
        if not row or not row[0]:
            return False
        if message_type == "template":
            return True
        if message_type == "text":
            current = now if now is not None else time.time()
            return bool(row[1] and current - row[1] <= 24 * 60 * 60)
        return False

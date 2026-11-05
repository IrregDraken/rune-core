from __future__ import annotations

"""Durable, fail-closed consent ledger for outbound messaging."""

import sqlite3
import time
from contextlib import contextmanager
from typing import Iterator
from pathlib import Path


class MessagingConsentRegistry:
    def __init__(self, database_path: str | None = None) -> None:
        configured = database_path or "~/.rune/consent.sqlite3"
        self.path = Path(configured).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._session() as db:
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

    def record_webhook_event(self, channel: str, event_id: str) -> bool:
        """Atomically claim a provider event ID; duplicate webhook deliveries are ignored."""
        import re
        key = str(event_id).strip()
        if not key or len(key) > 256 or not re.fullmatch(r"[A-Za-z0-9_.:-]+", key):
            return False
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS processed_messaging_events (
                    channel TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    processed_at REAL NOT NULL,
                    PRIMARY KEY (channel, event_id)
                )
            """)
            cursor = db.execute("""
                INSERT OR IGNORE INTO processed_messaging_events
                    (channel, event_id, processed_at) VALUES (?, ?, ?)
            """, (channel.strip().lower(), key, time.time()))
            return cursor.rowcount == 1

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

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
            return bool(row[1] and 0 <= current - row[1] <= 24 * 60 * 60)
        return False


class WhatsAppWebhookVerifier:
    """Verify Meta webhook signatures and ingest only authenticated inbound events."""

    @staticmethod
    def verify_signature(raw_body: bytes, signature: str, app_secret: str) -> bool:
        import hashlib
        import hmac
        if not app_secret or not signature.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(
            app_secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def ingest(payload: dict, registry: MessagingConsentRegistry) -> dict:
        """Record verified inbound messages; START/STOP provide explicit consent signals."""
        import datetime
        accepted = 0
        opted_in = 0
        revoked = 0
        entries = payload.get("entry", [])
        if not isinstance(entries, list):
            raise ValueError("invalid_whatsapp_webhook_payload")
        for entry in entries:
            changes = entry.get("changes", []) if isinstance(entry, dict) else []
            if not isinstance(changes, list):
                continue
            for change in changes:
                value = change.get("value", {}) if isinstance(change, dict) else {}
                messages = value.get("messages", []) if isinstance(value, dict) else []
                if not isinstance(messages, list):
                    continue
                for message in messages:
                    if not isinstance(message, dict):
                        continue
                    sender = str(message.get("from", "")).strip()
                    try:
                        registry._recipient(sender)
                    except ValueError:
                        continue
                    stamp = message.get("timestamp")
                    try:
                        event_time = float(stamp)
                    except (TypeError, ValueError):
                        continue
                    if event_time <= 0 or event_time > __import__("time").time() + 300:
                        continue
                    event_id = str(message.get("id", "")).strip()
                    if not registry.record_webhook_event("whatsapp", event_id):
                        continue
                    registry.record_inbound("whatsapp", sender, timestamp=event_time)
                    accepted += 1
                    text_value = message.get("text", {})
                    text_body = str(
                        text_value.get("body", "") if isinstance(text_value, dict) else ""
                    ).strip().upper()
                    if text_body in {"START", "SUBSCRIBE", "YES"}:
                        registry.record_opt_in("whatsapp", sender, "verified_inbound_keyword:" + text_body)
                        opted_in += 1
                    elif text_body in {"STOP", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"}:
                        registry.revoke("whatsapp", sender, "verified_inbound_keyword:" + text_body)
                        revoked += 1
        return {"inbound_recorded": accepted, "opted_in": opted_in, "revoked": revoked}

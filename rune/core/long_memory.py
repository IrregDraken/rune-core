from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MemoryRecord:
    key: str
    value: Any
    kind: str = "semantic"
    salience: float = 0.5
    confidence: float = 1.0
    tags: tuple[str, ...] = ()
    created_at: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0


@dataclass
class LongTermMemory:
    """Durable, bounded memory index with a dependency-free SQLite backend.

    The retrieval contract stays provider-neutral so an embedding/vector
    backend can replace lexical ranking later without changing the runtime.
    """

    db_path: str | Path | None = None
    records: dict[str, MemoryRecord] = field(default_factory=dict)
    _db: sqlite3.Connection | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.db_path is not None:
            path = Path(self.db_path)
            if str(path) != ":memory:" and path.parent != Path("."):
                path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(path))
            self._db.execute(
                """CREATE TABLE IF NOT EXISTS memories (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    salience REAL NOT NULL,
                    confidence REAL NOT NULL,
                    tags TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER NOT NULL
                )"""
            )
            self._db.commit()
            self._load()

    def _load(self) -> None:
        if self._db is None:
            return
        rows = self._db.execute(
            "SELECT key,value,kind,salience,confidence,tags,created_at,last_accessed,access_count FROM memories"
        ).fetchall()
        for row in rows:
            try:
                value = json.loads(row[1])
                tags = tuple(json.loads(row[5]))
            except (json.JSONDecodeError, TypeError):
                value, tags = row[1], ()
            self.records[row[0]] = MemoryRecord(
                key=row[0],
                value=value,
                kind=row[2],
                salience=float(row[3]),
                confidence=float(row[4]),
                tags=tags,
                created_at=float(row[6]),
                last_accessed=float(row[7]),
                access_count=int(row[8]),
            )

    def _persist(self, record: MemoryRecord) -> None:
        if self._db is None:
            return
        self._db.execute(
            """INSERT INTO memories
               (key,value,kind,salience,confidence,tags,created_at,last_accessed,access_count)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(key) DO UPDATE SET
                 value=excluded.value,
                 kind=excluded.kind,
                 salience=excluded.salience,
                 confidence=excluded.confidence,
                 tags=excluded.tags,
                 last_accessed=excluded.last_accessed,
                 access_count=excluded.access_count""",
            (
                record.key,
                json.dumps(record.value, default=str),
                record.kind,
                record.salience,
                record.confidence,
                json.dumps(record.tags),
                record.created_at,
                record.last_accessed,
                record.access_count,
            ),
        )
        self._db.commit()

    def remember(
        self,
        key: str,
        value: Any,
        *,
        kind: str = "semantic",
        salience: float = 0.5,
        confidence: float = 1.0,
        tags: tuple[str, ...] = (),
    ) -> MemoryRecord:
        now = time.time()
        salience = min(1.0, max(0.0, salience))
        confidence = min(1.0, max(0.0, confidence))
        record = self.records.get(key)
        if record is None:
            record = MemoryRecord(key, value, kind, salience, confidence, tags, now, now, 0)
        else:
            record.value = value
            record.kind = kind
            record.salience = salience
            record.confidence = confidence
            record.tags = tags
            record.last_accessed = now
        self.records[key] = record
        self._persist(record)
        return record

    def recall(self, key: str) -> Any | None:
        record = self.records.get(key)
        if record is None:
            return None
        record.access_count += 1
        record.last_accessed = time.time()
        self._persist(record)
        return record.value

    def search(self, query: str, limit: int = 8) -> list[MemoryRecord]:
        tokens = {token for token in query.lower().split() if len(token) > 2}
        now = time.time()
        scored: list[tuple[float, MemoryRecord]] = []
        for record in self.records.values():
            haystack = f"{record.key} {record.value} {' '.join(record.tags)}".lower()
            lexical = sum(token in haystack for token in tokens) / max(1, len(tokens))
            recency = 1.0 / (1.0 + max(0.0, now - record.last_accessed) / 86400)
            score = (
                0.50 * lexical
                + 0.20 * record.salience
                + 0.15 * record.confidence
                + 0.15 * recency
            )
            scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        results = [record for _, record in scored[: max(0, limit)]]
        for record in results:
            record.access_count += 1
            record.last_accessed = now
            self._persist(record)
        return results

    def snapshot(self) -> list[dict[str, Any]]:
        return [record.__dict__.copy() for record in self.records.values()]

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None

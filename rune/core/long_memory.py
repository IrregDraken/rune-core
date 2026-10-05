from __future__ import annotations

from dataclasses import dataclass, field
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
    """Small dependency-free memory index.

    Retrieval is deliberately explicit and bounded. A future vector/embedding
    backend can implement the same contract without changing cognition.
    """

    records: dict[str, MemoryRecord] = field(default_factory=dict)

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
        import time
        now = time.time()
        record = self.records.get(key)
        if record is None:
            record = MemoryRecord(key, value, kind, salience, confidence, tags, now, now, 0)
        else:
            record.value = value
            record.salience = salience
            record.confidence = confidence
            record.tags = tags
            record.last_accessed = now
        self.records[key] = record
        return record

    def recall(self, key: str) -> Any | None:
        record = self.records.get(key)
        if record is None:
            return None
        record.access_count += 1
        import time
        record.last_accessed = time.time()
        return record.value

    def search(self, query: str, limit: int = 8) -> list[MemoryRecord]:
        import time
        tokens = {token for token in query.lower().split() if len(token) > 2}
        now = time.time()
        scored: list[tuple[float, MemoryRecord]] = []
        for record in self.records.values():
            haystack = f"{record.key} {record.value} {' '.join(record.tags)}".lower()
            lexical = sum(token in haystack for token in tokens) / max(1, len(tokens))
            recency = 1.0 / (1.0 + max(0.0, now - record.last_accessed) / 86400)
            score = (0.55 * lexical) + (0.25 * record.salience) + (0.20 * recency)
            scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        results = [record for _, record in scored[:limit]]
        for record in results:
            record.access_count += 1
            record.last_accessed = now
        return results

    def snapshot(self) -> list[dict[str, Any]]:
        return [record.__dict__.copy() for record in self.records.values()]

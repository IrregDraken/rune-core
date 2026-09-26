from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class MemoryStore(Protocol):
    def remember(self, key: str, value: Any) -> None: ...
    def recall(self, key: str) -> Any | None: ...


@dataclass
class WorkingMemory:
    """Small active workspace. Long-term storage comes later."""

    capacity: int = 32
    _items: dict[str, Any] = field(default_factory=dict)

    def remember(self, key: str, value: Any) -> None:
        if key not in self._items and len(self._items) >= self.capacity:
            oldest = next(iter(self._items))
            del self._items[oldest]
        self._items[key] = value

    def recall(self, key: str) -> Any | None:
        return self._items.get(key)

    def snapshot(self) -> dict[str, Any]:
        return dict(self._items)

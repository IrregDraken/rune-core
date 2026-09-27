from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol
from .memory import WorkingMemory

class Retriever(Protocol):
    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]: ...

@dataclass
class ContextAssembler:
    memory: WorkingMemory
    max_items: int = 16
    max_chars: int = 12000
    def build(self, user_input: str, retrieved: list[dict[str, Any]] | None = None) -> str:
        lines=["RUNE CONTEXT",f"USER INPUT: {user_input}","","ACTIVE MEMORY:"]
        for key,value in list(self.memory.snapshot().items())[-self.max_items:]:
            lines.append(f"- {key}: {value}")
        if retrieved:
            lines += ["","RETRIEVED EVIDENCE:"]
            for item in retrieved:
                lines.append(f"- {item.get('title','Untitled')} | {item.get('source','')}\n  {item.get('text','')}")
        return "\n".join(lines)[:self.max_chars]

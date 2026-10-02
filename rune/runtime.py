from __future__ import annotations

import platform
import socket

from .core.commands import ParsedCommand, parse_command
from .core.context import ContextAssembler, Retriever
from .core.engine import RUNEEngine
from .core.model import ModelProvider
from .core.node import NodeInfo, NullNode, RUNEActionNode
from .core.persistence import SQLiteEventStore

class RUNERuntime:
    """Composition root for a persistent local RUNE process."""

    def __init__(
        self,
        model: ModelProvider,
        db_path: str = "data/rune.db",
        retriever: Retriever | None = None,
        node: RUNEActionNode | None = None,
    ) -> None:
        self.engine = RUNEEngine(model)
        self.store = SQLiteEventStore(db_path)
        self.retriever = retriever
        self.context = ContextAssembler(self.engine.memory)
        self.node = node or NullNode(NodeInfo(
            node_id="local",
            platform=platform.system().lower(),
            hostname=socket.gethostname(),
        ))
        self._persisted_events = 0

    def parse_command(self, text: str) -> ParsedCommand:
        return parse_command(text)

    def receive(self, text: str) -> str:
        parsed = self.parse_command(text)
        if parsed.command is not None:
            self.engine.memory.remember("last_command", parsed.command.value)
        evidence = self.retriever.search(text) if self.retriever else []
        prompt = self.context.build(text, evidence)
        response = self.engine.receive(text, model_input=prompt)
        self._persist_new_events()
        return response

    def _persist_new_events(self) -> None:
        events = self.engine.state.events
        for event in events[self._persisted_events:]:
            self.store.append(event)
        self._persisted_events = len(events)

    def recent_events(self, limit: int = 50) -> list[dict]:
        return self.store.recent(limit)

    def snapshot(self) -> dict:
        state = self.engine.state
        info = self.node.info()
        return {
            "identity": {"name": state.identity.name, "role": state.identity.role},
            "current_goal": state.current_goal,
            "active_context": state.active_context,
            "working_memory": self.engine.memory.snapshot(),
            "last_decision": state.last_decision.__dict__ if state.last_decision else None,
            "last_action": state.last_action.__dict__ if state.last_action else None,
            "node": {
                "id": info.node_id,
                "platform": info.platform,
                "hostname": info.hostname,
                "capabilities": sorted(capability.value for capability in info.capabilities),
            },
        }

    def close(self) -> None:
        self.store.close()

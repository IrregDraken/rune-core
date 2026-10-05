from __future__ import annotations

import platform
import socket

from .core.commands import ParsedCommand, parse_command
from .core.authority import Authority
from .core.cognition import CognitionEngine
from .core.long_memory import LongTermMemory
from .core.planning import Planner, Plan
from .core.context import ContextAssembler, Retriever
from .core.identity import IdentityProvider, LocalIdentityProvider
from .core.tools import ToolRegistry
from .core.voice import VoicePipeline
from .core.engine import RUNEEngine
from .core.model import ModelProvider
from .core.node import NodeInfo, NullNode, RUNEActionNode
from .core.persistence import SQLiteEventStore

try:
    from .nodes.windows import WindowsNode
except ImportError:  # pragma: no cover - platform-specific adapter
    WindowsNode = None  # type: ignore[assignment]


class RUNERuntime:
    """Composition root for a persistent local RUNE process."""

    def __init__(
        self,
        model: ModelProvider,
        db_path: str = "data/rune.db",
        retriever: Retriever | None = None,
        node: RUNEActionNode | None = None,
        authority: Authority | None = None,
        identity: IdentityProvider | None = None,
        tools: ToolRegistry | None = None,
        voice: VoicePipeline | None = None,
        cognition: CognitionEngine | None = None,
        long_memory: LongTermMemory | None = None,
        planner: Planner | None = None,
    ) -> None:
        self.engine = RUNEEngine(model)
        self.cognition = cognition or CognitionEngine()
        self.long_memory = long_memory or LongTermMemory(db_path)
        self.planner = planner or Planner()
        self.active_plan: Plan | None = None
        self.store = SQLiteEventStore(db_path)
        self.retriever = retriever
        self.context = ContextAssembler(self.engine.memory)
        self.authority = authority or Authority.create()
        self.identity = identity or LocalIdentityProvider()
        self.tools = tools or ToolRegistry()
        self.voice = voice or VoicePipeline()
        if node is not None:
            self.node = node
        elif platform.system().lower() == "windows" and WindowsNode is not None:
            self.node = WindowsNode()
        else:
            self.node = NullNode(NodeInfo(
                node_id="local",
                platform=platform.system().lower(),
                hostname=socket.gethostname(),
            ))
        self._persisted_events = 0

    def parse_command(self, text: str) -> ParsedCommand:
        return parse_command(text)

    def set_goal(self, goal: str) -> str:
        """Set and persist the active goal used by cognition and planning."""
        clean = goal.strip()
        if not clean:
            raise ValueError("goal cannot be empty")
        self.engine.state.current_goal = clean
        self.long_memory.remember(
            "goal:current",
            clean,
            kind="goal",
            salience=1.0,
            confidence=1.0,
            tags=("goal", "current"),
        )
        return clean

    def remember(self, key: str, value: object, *, kind: str = "semantic", salience: float = 0.8, tags: tuple[str, ...] = ()) -> dict:
        """Persist an explicit memory without exposing storage details to callers."""
        record = self.long_memory.remember(
            key,
            value,
            kind=kind,
            salience=salience,
            confidence=1.0,
            tags=tags,
        )
        return record.__dict__.copy()

    def receive(self, text: str) -> str:
        parsed = self.parse_command(text)
        if parsed.command is not None:
            self.engine.memory.remember("last_command", parsed.command.value)

        assessment = self.cognition.assess(
            text,
            context={"current_goal": self.engine.state.current_goal},
        )
        self.engine.memory.remember("cognitive_mode", assessment.mode.value)
        self.engine.memory.remember("attention_score", assessment.attention_score)

        normalized = text.strip()
        lowered = normalized.lower()
        if lowered.startswith("remember that "):
            fact = normalized[len("remember that "):].strip()
            if fact:
                key = f"episodic:{int(__import__('time').time() * 1000)}"
                self.long_memory.remember(
                    key,
                    fact,
                    kind="episodic",
                    salience=max(0.65, assessment.significance),
                    confidence=1.0,
                    tags=("explicit", "user"),
                )
        elif lowered.startswith("my goal is "):
            self.set_goal(normalized[len("my goal is "):])

        memory_hits = self.long_memory.search(text)
        for record in memory_hits[:4]:
            self.engine.memory.remember(f"memory:{record.key}", record.value)
        evidence = self.retriever.search(text) if self.retriever else []
        prompt = self.context.build(text, evidence)
        response = self.engine.receive(text, model_input=prompt)
        self.engine.state.active_context = {
            "cognitive_mode": assessment.mode.value,
            "attention_score": assessment.attention_score,
            "urgency": assessment.urgency,
            "uncertainty": assessment.uncertainty,
            "significance": assessment.significance,
        }
        self._persist_new_events()
        return response

    def execute_action(
        self,
        capability,
        arguments: dict[str, str],
        *,
        authorized: bool = False,
    ) -> dict:
        """Run decision -> attempt -> node execution -> verification."""
        from uuid import uuid4
        from .core.agency import ActionRequest
        from .core.models import Event, EventType
        from .core.node import NodeAction

        action_id = str(uuid4())
        decision, result = self.engine.request_action(
            ActionRequest(
                intent=f"{capability.value} requested",
                capability=capability.value,
                authorized=authorized,
                feasible=self.node.can(capability),
                risk="high" if authorized else "blocked",
            ),
            action_id,
        )
        if result.status.value != "attempted":
            self._persist_new_events()
            return {
                "action_id": action_id,
                "decision": decision.__dict__,
                "result": result.__dict__,
            }

        action = NodeAction(capability, arguments, authorized=authorized)
        node_result = self.node.execute(action)
        self.engine.state.record(
            Event(
                EventType.ACTION_RESULT,
                {"action_id": action_id, "node_result": node_result},
            )
        )
        evidence = self.node.verify(action)
        verified = self.engine.verify_action(result, evidence)
        self._persist_new_events()
        return {
            "action_id": action_id,
            "decision": decision.__dict__,
            "node_result": node_result,
            "result": verified.__dict__,
        }

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
            "identity": {
                "name": state.identity.name,
                "role": state.identity.role,
                "owner": self.identity.current().__dict__,
            },
            "cognition": self.cognition.snapshot(),
            "long_term_memory": self.long_memory.snapshot()[-32:],
            "active_plan": self.active_plan.__dict__ if self.active_plan else None,
            "tools": [spec.__dict__ for spec in self.tools.specs()],
            "voice": {
                "wake_word": self.voice.wake_word is not None,
                "speech_to_text": self.voice.speech_to_text is not None,
                "text_to_speech": self.voice.text_to_speech is not None,
                "speaker_verifier": self.voice.speaker_verifier is not None,
            },
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
                "observation": self.node.observe(),
            },
        }

    def close(self) -> None:
        self.long_memory.close()
        self.store.close()

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class EventType(str, Enum):
    INPUT = "input"
    OBSERVATION = "observation"
    DECISION = "decision"
    ACTION_ATTEMPT = "action_attempt"
    ACTION_RESULT = "action_result"
    VERIFICATION = "verification"


class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    DENIED = "denied"
    BLOCKED = "blocked"


class ActionStatus(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    ATTEMPTED = "attempted"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RUNEIdentity:
    name: str = "RUNE"
    role: str = "persistent personal intelligence"


@dataclass
class Event:
    type: EventType
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=now_utc)


@dataclass
class Decision:
    intent: str
    status: DecisionStatus
    feasible: bool
    authorized: bool
    risk: str = "unknown"
    rationale: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=now_utc)


@dataclass
class ActionResult:
    action_id: str
    status: ActionStatus
    evidence: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    timestamp: datetime = field(default_factory=now_utc)


@dataclass
class RuntimeState:
    identity: RUNEIdentity = field(default_factory=RUNEIdentity)
    active_context: dict[str, Any] = field(default_factory=dict)
    current_goal: str | None = None
    events: list[Event] = field(default_factory=list)
    last_decision: Decision | None = None
    last_action: ActionResult | None = None

    def record(self, event: Event) -> None:
        self.events.append(event)

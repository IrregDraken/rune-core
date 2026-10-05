from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CognitiveMode(str, Enum):
    OBSERVE = "observe"
    REASON = "reason"
    PLAN = "plan"
    ACT = "act"
    VERIFY = "verify"


@dataclass(frozen=True)
class CognitiveSignal:
    name: str
    value: float
    rationale: str = ""


@dataclass
class CognitiveAssessment:
    input_text: str
    salience: float
    urgency: float
    uncertainty: float
    significance: float
    mode: CognitiveMode
    signals: list[CognitiveSignal] = field(default_factory=list)

    @property
    def attention_score(self) -> float:
        return min(1.0, max(0.0, (self.salience + self.urgency + self.significance) / 3))


@dataclass
class Goal:
    description: str
    priority: float = 0.5
    status: str = "active"


class CognitionEngine:
    """Deterministic appraisal layer around the model.

    It does not replace an LLM. It provides explicit state and bounded
    reasoning signals so model output can be grounded in runtime context.
    """

    def __init__(self) -> None:
        self.mode = CognitiveMode.OBSERVE
        self.goals: list[Goal] = []
        self.last_assessment: CognitiveAssessment | None = None

    def assess(self, text: str, *, context: dict[str, Any] | None = None) -> CognitiveAssessment:
        context = context or {}
        normalized = text.strip().lower()
        urgent_terms = ("urgent", "asap", "immediately", "emergency", "now")
        action_terms = ("open", "close", "start", "stop", "send", "run", "do", "fix")
        question_terms = ("why", "how", "what", "when", "where", "can you")

        urgency = 0.85 if any(term in normalized for term in urgent_terms) else 0.2
        salience = 0.75 if any(term in normalized for term in action_terms) else 0.45
        significance = 0.7 if context.get("current_goal") else 0.4
        uncertainty = 0.7 if not normalized or normalized.endswith("?") else 0.35

        if any(term in normalized for term in action_terms):
            mode = CognitiveMode.ACT if urgency < 0.8 else CognitiveMode.PLAN
        elif any(term in normalized for term in question_terms):
            mode = CognitiveMode.REASON
        else:
            mode = CognitiveMode.OBSERVE

        assessment = CognitiveAssessment(
            input_text=text,
            salience=salience,
            urgency=urgency,
            uncertainty=uncertainty,
            significance=significance,
            mode=mode,
            signals=[
                CognitiveSignal("salience", salience),
                CognitiveSignal("urgency", urgency),
                CognitiveSignal("uncertainty", uncertainty),
                CognitiveSignal("significance", significance),
            ],
        )
        self.mode = mode
        self.last_assessment = assessment
        return assessment

    def set_goal(self, description: str, priority: float = 0.5) -> Goal:
        goal = Goal(description=description, priority=max(0.0, min(1.0, priority)))
        self.goals.append(goal)
        return goal

    def snapshot(self) -> dict[str, Any]:
        assessment = self.last_assessment
        return {
            "mode": self.mode.value,
            "assessment": {
                "input": assessment.input_text,
                "salience": assessment.salience,
                "urgency": assessment.urgency,
                "uncertainty": assessment.uncertainty,
                "significance": assessment.significance,
                "attention_score": assessment.attention_score,
            } if assessment else None,
            "goals": [goal.__dict__ for goal in self.goals],
        }

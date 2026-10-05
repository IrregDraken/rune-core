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
    control: float = 0.5
    consequence: float = 0.2
    goal_pressure: float = 0.0
    prediction_error: float = 0.0
    signals: list[CognitiveSignal] = field(default_factory=list)

    @property
    def attention_score(self) -> float:
        return min(
            1.0,
            max(
                0.0,
                0.25 * self.salience
                + 0.25 * self.urgency
                + 0.20 * self.significance
                + 0.15 * self.consequence
                + 0.15 * self.goal_pressure,
            ),
        )


@dataclass
class Goal:
    description: str
    priority: float = 0.5
    status: str = "active"


class CognitionEngine:
    """Deterministic appraisal layer around the model.

    It does not replace an LLM. It provides explicit, bounded appraisal
    signals that can steer reasoning, planning and verification.
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
        low_control_terms = ("can't", "cannot", "unable", "blocked", "stuck", "failed")
        high_consequence_terms = (
            "delete", "shutdown", "reboot", "transfer", "pay", "send", "publish", "remove"
        )

        urgency = 0.85 if any(term in normalized for term in urgent_terms) else 0.2
        salience = 0.75 if any(term in normalized for term in action_terms) else 0.45
        significance = 0.7 if context.get("current_goal") else 0.4
        uncertainty = 0.7 if not normalized or normalized.endswith("?") else 0.35
        control = 0.25 if any(term in normalized for term in low_control_terms) else 0.7
        consequence = 0.85 if any(term in normalized for term in high_consequence_terms) else 0.2

        goal_text = str(context.get("current_goal") or "").lower()
        goal_tokens = {token for token in goal_text.split() if len(token) > 2}
        input_tokens = {token for token in normalized.split() if len(token) > 2}
        overlap = len(goal_tokens & input_tokens) / max(1, len(goal_tokens))
        goal_priority = max((goal.priority for goal in self.goals if goal.status == "active"), default=0.0)
        goal_pressure = min(1.0, 0.7 * overlap + 0.3 * goal_priority)

        expected = context.get("expected_outcome")
        observed = context.get("observed_outcome")
        prediction_error = 0.0 if expected is None or observed is None else (
            0.0 if expected == observed else 1.0
        )

        if consequence >= 0.8 or (uncertainty >= 0.7 and salience >= 0.7):
            mode = CognitiveMode.PLAN
        elif any(term in normalized for term in action_terms):
            mode = CognitiveMode.ACT
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
            control=control,
            consequence=consequence,
            goal_pressure=goal_pressure,
            prediction_error=prediction_error,
            signals=[
                CognitiveSignal("salience", salience),
                CognitiveSignal("urgency", urgency),
                CognitiveSignal("uncertainty", uncertainty),
                CognitiveSignal("significance", significance),
                CognitiveSignal("control", control),
                CognitiveSignal("consequence", consequence),
                CognitiveSignal("goal_pressure", goal_pressure),
                CognitiveSignal("prediction_error", prediction_error),
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
                "control": assessment.control,
                "consequence": assessment.consequence,
                "goal_pressure": assessment.goal_pressure,
                "prediction_error": assessment.prediction_error,
            } if assessment else None,
            "goals": [goal.__dict__ for goal in self.goals],
        }

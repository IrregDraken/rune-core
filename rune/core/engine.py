from __future__ import annotations

from .agency import ActionRequest, Agency
from .memory import WorkingMemory
from .model import ModelProvider
from .models import Event, EventType, RuntimeState


class RUNEEngine:
    """Executable RUNE kernel. The model is a replaceable cognition component."""

    def __init__(
        self,
        model: ModelProvider,
        memory: WorkingMemory | None = None,
        agency: Agency | None = None,
    ) -> None:
        self.model = model
        self.memory = memory or WorkingMemory()
        self.agency = agency or Agency()
        self.state = RuntimeState()

    def receive(self, text: str, *, model_input: str | None = None) -> str:
        self.state.record(Event(EventType.INPUT, {"text": text}))
        self.memory.remember("last_input", text)

        response = self.model.respond(model_input if model_input is not None else text)
        self.state.record(
            Event(
                EventType.OBSERVATION,
                {"content": response.content, "confidence": response.confidence},
            )
        )
        return response.content

    def request_action(self, request: ActionRequest, action_id: str):
        decision = self.agency.decide(request)
        self.state.last_decision = decision
        self.state.record(
            Event(
                EventType.DECISION,
                {
                    "intent": decision.intent,
                    "status": decision.status.value,
                    "feasible": decision.feasible,
                    "authorized": decision.authorized,
                },
            )
        )

        result = self.agency.record_attempt(decision, action_id)
        self.state.last_action = result
        self.state.record(
            Event(
                EventType.ACTION_ATTEMPT,
                {"action_id": action_id, "status": result.status.value},
            )
        )
        return decision, result

    def verify_action(self, result, evidence: dict):
        verified = self.agency.verify(result, evidence)
        self.state.last_action = verified
        self.state.record(
            Event(
                EventType.VERIFICATION,
                {
                    "action_id": verified.action_id,
                    "status": verified.status.value,
                    "evidence": verified.evidence,
                },
            )
        )
        return verified

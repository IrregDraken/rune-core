from __future__ import annotations

from dataclasses import dataclass

from .models import ActionResult, ActionStatus, Decision, DecisionStatus


@dataclass(frozen=True)
class ActionRequest:
    intent: str
    capability: str
    authorized: bool = False
    feasible: bool = True
    risk: str = "unknown"


class Agency:
    """Controls the boundary between decisions and real-world actions."""

    def decide(self, request: ActionRequest) -> Decision:
        if not request.feasible:
            status = DecisionStatus.BLOCKED
            rationale = "Action is not feasible under current constraints."
        elif not request.authorized:
            status = DecisionStatus.DENIED
            rationale = "Required authority has not been granted."
        else:
            status = DecisionStatus.APPROVED
            rationale = "Action satisfies current feasibility and authority checks."

        return Decision(
            intent=request.intent,
            status=status,
            feasible=request.feasible,
            authorized=request.authorized,
            risk=request.risk,
            rationale=rationale,
        )

    def record_attempt(self, decision: Decision, action_id: str) -> ActionResult:
        if decision.status is not DecisionStatus.APPROVED:
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.NOT_ATTEMPTED,
                message="Execution was not permitted by the decision.",
            )

        return ActionResult(
            action_id=action_id,
            status=ActionStatus.ATTEMPTED,
            message="Execution was attempted; outcome requires external observation.",
        )

    def verify(self, result: ActionResult, evidence: dict) -> ActionResult:
        if result.status is not ActionStatus.ATTEMPTED:
            return result
        confirmed = bool(evidence.get("confirmed"))
        return ActionResult(
            action_id=result.action_id,
            status=ActionStatus.SUCCEEDED if confirmed else ActionStatus.UNKNOWN,
            evidence=evidence,
            message="Outcome verified." if confirmed else "Outcome remains unverified.",
        )

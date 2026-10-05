from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PlanStatus(str, Enum):
    PROPOSED = "proposed"
    READY = "ready"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class PlanStep:
    id: str
    description: str
    capability: str | None = None
    requires_authority: bool = False
    status: PlanStatus = PlanStatus.PROPOSED
    verification: dict = field(default_factory=dict)


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep]
    status: PlanStatus = PlanStatus.PROPOSED

    def next_step(self) -> PlanStep | None:
        for step in self.steps:
            if step.status in (PlanStatus.PROPOSED, PlanStatus.READY):
                return step
        return None


class Planner:
    """Conservative plan container.

    It does not execute anything. Execution remains owned by the agency/node
    pipeline, keeping planning separate from authority.
    """

    def create(self, goal: str, steps: list[PlanStep]) -> Plan:
        plan = Plan(goal=goal, steps=steps, status=PlanStatus.READY if steps else PlanStatus.BLOCKED)
        if steps:
            steps[0].status = PlanStatus.READY
        return plan

    def mark_executing(self, plan: Plan, step_id: str) -> None:
        step = self._step(plan, step_id)
        if step:
            step.status = PlanStatus.EXECUTING
            plan.status = PlanStatus.EXECUTING

    def verify_step(self, plan: Plan, step_id: str, evidence: dict) -> PlanStep | None:
        step = self._step(plan, step_id)
        if step is None:
            return None
        step.verification = dict(evidence)
        if evidence.get("confirmed") is True:
            step.status = PlanStatus.COMPLETE
            next_step = plan.next_step()
            if next_step:
                next_step.status = PlanStatus.READY
            else:
                plan.status = PlanStatus.COMPLETE
        elif evidence.get("confirmed") is False:
            step.status = PlanStatus.FAILED
            plan.status = PlanStatus.FAILED
        return step

    @staticmethod
    def _step(plan: Plan, step_id: str) -> PlanStep | None:
        return next((step for step in plan.steps if step.id == step_id), None)

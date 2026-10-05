from rune.core.planning import PlanStatus, PlanStep, Planner


def test_plan_advances_only_after_verification():
    planner = Planner()
    plan = planner.create("finish task", [
        PlanStep("one", "do first"),
        PlanStep("two", "do second"),
    ])
    assert plan.next_step().id == "one"
    planner.mark_executing(plan, "one")
    planner.verify_step(plan, "one", {"confirmed": True})
    assert plan.steps[0].status is PlanStatus.COMPLETE
    assert plan.next_step().id == "two"
    assert plan.steps[1].status is PlanStatus.READY

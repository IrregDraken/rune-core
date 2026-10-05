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


def test_plan_round_trips():
    planner = Planner()
    plan = planner.create("ship RUNE", [
        PlanStep("one", "build core", capability="file_write", requires_authority=True),
        PlanStep("two", "verify build"),
    ])
    restored = planner.restore(plan.to_dict())
    assert restored.goal == "ship RUNE"
    assert restored.steps[0].requires_authority is True
    assert restored.steps[0].status is PlanStatus.READY

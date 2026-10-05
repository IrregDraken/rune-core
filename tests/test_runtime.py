from pathlib import Path

from rune.core.model import DeterministicModel
from rune.core.persistence import SQLiteEventStore
from rune.runtime import RUNERuntime


def test_runtime_persists_events(tmp_path: Path):
    db = tmp_path / "rune.db"
    runtime = RUNERuntime(DeterministicModel(), db_path=str(db))
    result = runtime.receive("Remember this test.")
    runtime.close()

    store = SQLiteEventStore(db)
    events = store.recent(10)
    store.close()

    assert "Remember this test." in result
    assert len(events) == 2
    assert events[-1]["type"] == "input"


def test_runtime_persists_each_turn_once(tmp_path: Path):
    runtime = RUNERuntime(DeterministicModel(), db_path=str(tmp_path / "rune.db"))
    runtime.receive("first")
    runtime.receive("second")

    events = runtime.recent_events(10)
    runtime.close()

    assert len(events) == 4
    assert [event["type"] for event in reversed(events)] == [
        "input",
        "observation",
        "input",
        "observation",
    ]


def test_context_contains_memory():
    runtime = RUNERuntime(DeterministicModel(), db_path=":memory:")
    runtime.engine.memory.remember("project", "RUNE")
    prompt = runtime.context.build("continue")
    runtime.close()
    assert "project: RUNE" in prompt


def test_runtime_persists_explicit_memory_and_goal(tmp_path: Path):
    db = tmp_path / "rune.db"
    runtime = RUNERuntime(DeterministicModel(), db_path=str(db))
    runtime.receive("Remember that RUNE should feel like home.")
    runtime.set_goal("Ship the RUNE core")
    runtime.close()

    restored = RUNERuntime(DeterministicModel(), db_path=str(db))
    assert any(
        "feel like home" in str(record.value)
        for record in restored.long_memory.records.values()
    )
    assert restored.long_memory.recall("goal:current") == "Ship the RUNE core"
    restored.close()


def test_runtime_restores_active_plan(tmp_path: Path):
    db = tmp_path / "rune.db"
    runtime = RUNERuntime(DeterministicModel(), db_path=str(db))
    runtime.create_plan("ship", [{"id": "one", "description": "run tests"}])
    runtime.close()

    restored = RUNERuntime(DeterministicModel(), db_path=str(db))
    assert restored.active_plan is not None
    assert restored.active_plan.goal == "ship"
    assert restored.active_plan.steps[0].status.value == "ready"
    restored.close()

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

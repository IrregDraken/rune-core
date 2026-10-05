from rune.core.long_memory import LongTermMemory


def test_memory_retrieval_prefers_relevant_content():
    memory = LongTermMemory()
    memory.remember("project", "RUNE cognition architecture", salience=0.9, tags=("rune", "cognition"))
    memory.remember("weather", "rain tomorrow", salience=0.2, tags=("weather",))
    result = memory.search("RUNE cognition", limit=1)
    assert result[0].key == "project"


def test_memory_survives_restart(tmp_path):
    path = tmp_path / "memory.db"
    first = LongTermMemory(path)
    first.remember("owner.preference", "green", kind="preference", tags=("owner", "preference"))
    first.close()

    second = LongTermMemory(path)
    assert second.recall("owner.preference") == "green"
    assert second.records["owner.preference"].kind == "preference"
    second.close()

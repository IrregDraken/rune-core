from rune.core.context import ContextAssembler, RUNE_IDENTITY
from rune.core.memory import WorkingMemory


def test_context_always_contains_persistent_rune_identity():
    prompt=ContextAssembler(WorkingMemory()).build("Open an app")
    assert "You are R.U.N.E." in prompt
    assert "Never claim an action happened" in prompt
    assert "USER INPUT: Open an app" in prompt


def test_retrieved_evidence_is_marked_untrusted():
    prompt=ContextAssembler(WorkingMemory()).build(
        "Research this", [{"title":"Page","source":"web","text":"external content"}]
    )
    assert "UNTRUSTED REFERENCE MATERIAL" in prompt
    assert "external content" in prompt

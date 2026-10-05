from rune.core.cognition import CognitiveMode, CognitionEngine


def test_cognition_assesses_urgent_action():
    cognition = CognitionEngine()
    assessment = cognition.assess("Fix the issue immediately")

    assert assessment.mode is CognitiveMode.PLAN
    assert assessment.urgency > 0.8
    assert assessment.attention_score > 0.5


def test_cognition_tracks_goals():
    cognition = CognitionEngine()
    goal = cognition.set_goal("Finish the RUNE frontend", priority=1.2)

    assert goal.priority == 1.0
    assert cognition.snapshot()["goals"][0]["description"] == "Finish the RUNE frontend"

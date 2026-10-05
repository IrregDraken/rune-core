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


def test_cognition_appraises_control_and_consequence():
    cognition = CognitionEngine()
    assessment = cognition.assess(
        "I am blocked, delete the old build now",
        context={"current_goal": "ship the build"},
    )

    assert assessment.control < 0.5
    assert assessment.consequence > 0.8
    assert assessment.mode is CognitiveMode.PLAN


def test_cognition_tracks_prediction_error():
    cognition = CognitionEngine()
    assessment = cognition.assess(
        "verify the action",
        context={"expected_outcome": "done", "observed_outcome": "failed"},
    )
    assert assessment.prediction_error == 1.0

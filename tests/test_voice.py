import pytest

from rune.core.voice import Speech, Transcript, VoiceInput, VoicePipeline


class FakeSTT:
    def transcribe(self, audio: VoiceInput) -> Transcript:
        return Transcript("hello rune", 0.99)


class FakeTTS:
    def synthesize(self, speech: Speech) -> bytes:
        return speech.text.encode()


def test_voice_pipeline_is_provider_neutral() -> None:
    pipeline = VoicePipeline(speech_to_text=FakeSTT(), text_to_speech=FakeTTS())
    transcript = pipeline.transcribe(VoiceInput(b"audio", 16000))
    assert transcript.text == "hello rune"
    assert pipeline.synthesize(Speech("hello")) == b"hello"


def test_voice_pipeline_requires_connected_provider() -> None:
    pipeline = VoicePipeline()
    with pytest.raises(RuntimeError):
        pipeline.transcribe(VoiceInput(b"audio", 16000))

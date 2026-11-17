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


import httpx
from rune.core.voice import ElevenLabsTextToSpeechProvider, VoiceProviderUnavailable


def test_elevenlabs_tts_uses_configured_voice_and_returns_audio(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers["xi-api-key"]
        seen["body"] = request.read().decode()
        return httpx.Response(200, content=b"fake-mp3-audio")

    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-secret")
    monkeypatch.setenv("RUNE_ELEVENLABS_VOICE_ID", "configured-voice")
    monkeypatch.setenv("RUNE_ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")
    provider = ElevenLabsTextToSpeechProvider(transport=httpx.MockTransport(handler))

    assert provider.synthesize(Speech("Hello, RUNE.")) == b"fake-mp3-audio"
    assert "/v1/text-to-speech/configured-voice" in seen["url"]
    assert seen["key"] == "test-secret"
    assert '"model_id":"eleven_flash_v2_5"' in seen["body"]


def test_elevenlabs_tts_requires_key_and_voice(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("RUNE_ELEVENLABS_VOICE_ID", raising=False)
    provider = ElevenLabsTextToSpeechProvider()
    with pytest.raises(VoiceProviderUnavailable):
        provider.synthesize(Speech("Hello"))


def test_elevenlabs_tts_rejects_long_interactive_responses():
    provider = ElevenLabsTextToSpeechProvider()
    with pytest.raises(ValueError):
        provider.synthesize(Speech("x" * 1001))

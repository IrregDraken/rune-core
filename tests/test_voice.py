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
from rune.core.voice import (ElevenLabsTextToSpeechProvider, OpenAISpeechToTextProvider, VoiceProviderUnavailable, VoiceInput, VoiceUsageLedger, VoiceBudgetExceeded, VoiceSessionController, VoiceSessionState)


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



def test_configured_voice_pipeline_only_connects_tts_with_key_and_voice(monkeypatch):
    from rune.core.voice import configured_voice_pipeline

    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("RUNE_ELEVENLABS_VOICE_ID", raising=False)
    assert configured_voice_pipeline().text_to_speech is None

    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("RUNE_ELEVENLABS_VOICE_ID", "test-voice")
    assert isinstance(
        configured_voice_pipeline().text_to_speech,
        ElevenLabsTextToSpeechProvider,
    )



def test_openai_transcription_uses_gpt_transcribe_and_multipart(monkeypatch):
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = request.read()
        return httpx.Response(200, json={"text": "  Hey RUNE.  "})

    monkeypatch.setenv("RUNE_OPENAI_STT_API_KEY", "stt-secret")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("RUNE_OPENAI_STT_MODEL_ID", raising=False)
    provider = OpenAISpeechToTextProvider(transport=httpx.MockTransport(handler))

    transcript = provider.transcribe(VoiceInput(b"wav-bytes", 16000, audio_format="wav"))
    assert transcript.text == "Hey RUNE."
    assert seen["url"] == "https://api.openai.com/v1/audio/transcriptions"
    assert seen["auth"] == "Bearer stt-secret"
    assert b'name="model"\r\n\r\ngpt-transcribe' in seen["body"]
    assert b'rune-utterance.wav' in seen["body"]


def test_openai_transcription_rejects_oversized_and_unknown_audio(monkeypatch):
    monkeypatch.setenv("RUNE_OPENAI_STT_API_KEY", "stt-secret")
    provider = OpenAISpeechToTextProvider()
    with pytest.raises(ValueError):
        provider.transcribe(VoiceInput(b"x" * (25 * 1024 * 1024 + 1), 16000))
    with pytest.raises(ValueError):
        provider.transcribe(VoiceInput(b"audio", 16000, audio_format="exe"))


def test_configured_voice_pipeline_connects_stt_separately_from_tts(monkeypatch):
    from rune.core.voice import configured_voice_pipeline

    monkeypatch.setenv("RUNE_OPENAI_STT_API_KEY", "stt-secret")
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("RUNE_ELEVENLABS_VOICE_ID", raising=False)
    pipeline = configured_voice_pipeline()
    assert isinstance(pipeline.speech_to_text, OpenAISpeechToTextProvider)
    assert pipeline.text_to_speech is None



def test_elevenlabs_monthly_character_budget_is_enforced(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-secret")
    monkeypatch.setenv("RUNE_ELEVENLABS_VOICE_ID", "configured-voice")
    ledger = VoiceUsageLedger(str(tmp_path / "voice.db"), monthly_limit=5)
    provider = ElevenLabsTextToSpeechProvider(
        usage_ledger=ledger,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"audio")),
    )
    provider.synthesize(Speech("1234"))
    assert ledger.spent() == 4
    with pytest.raises(VoiceBudgetExceeded):
        provider.synthesize(Speech("12"))
    ledger.close()



def test_voice_session_uses_two_minute_prompt_and_fifteen_second_close():
    session = VoiceSessionController(inactivity_seconds=120, confirmation_seconds=15)
    session.wake_detected(0)
    session.processing_started(5)
    session.speech_started(8)
    session.speech_finished(10)

    assert session.tick(129) is None
    assert session.tick(130) == "You still there, or are we good?"
    assert session.state == VoiceSessionState.WAITING_CONFIRMATION
    session.tick(144)
    assert session.state == VoiceSessionState.WAITING_CONFIRMATION
    session.tick(145)
    assert session.state == VoiceSessionState.STANDBY


def test_voice_session_can_resume_and_interrupt_without_touching_background_work():
    session = VoiceSessionController()
    session.wake_detected(0)
    session.speech_started(1)
    session.interrupt(2)
    assert session.state == VoiceSessionState.LISTENING

    session.last_activity_at = 2
    session.tick(122)
    session.answer_confirmation(True, 125)
    assert session.state == VoiceSessionState.LISTENING
    assert session.last_activity_at == 125


def test_voice_session_closes_when_owner_says_done():
    session = VoiceSessionController()
    session.wake_detected(0)
    session.tick(120)
    session.answer_confirmation(False, 121)
    assert session.state == VoiceSessionState.STANDBY

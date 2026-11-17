from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import os

import httpx


@dataclass(frozen=True)
class VoiceInput:
    audio: bytes
    sample_rate: int
    channels: int = 1


@dataclass(frozen=True)
class Transcript:
    text: str
    confidence: float | None = None
    speaker: str | None = None


@dataclass(frozen=True)
class Speech:
    text: str
    voice: str | None = None


class WakeWordProvider(Protocol):
    def detect(self, audio: VoiceInput) -> bool: ...


class SpeechToTextProvider(Protocol):
    def transcribe(self, audio: VoiceInput) -> Transcript: ...


class TextToSpeechProvider(Protocol):
    def synthesize(self, speech: Speech) -> bytes: ...


class SpeakerVerifier(Protocol):
    def verify(self, audio: VoiceInput, expected_subject: str) -> bool: ...


class VoicePipeline:
    """Provider-neutral voice boundary.

    Microphone capture, speech recognition, local wake-word detection and
    speaker verification remain separate adapters. TTS can be configured
    through the server-side ElevenLabs adapter.
    """

    def __init__(
        self,
        *,
        wake_word: WakeWordProvider | None = None,
        speech_to_text: SpeechToTextProvider | None = None,
        text_to_speech: TextToSpeechProvider | None = None,
        speaker_verifier: SpeakerVerifier | None = None,
    ) -> None:
        self.wake_word = wake_word
        self.speech_to_text = speech_to_text
        self.text_to_speech = text_to_speech
        self.speaker_verifier = speaker_verifier

    def transcribe(self, audio: VoiceInput) -> Transcript:
        if self.speech_to_text is None:
            raise RuntimeError("speech-to-text provider is not connected")
        return self.speech_to_text.transcribe(audio)

    def synthesize(self, speech: Speech) -> bytes:
        if self.text_to_speech is None:
            raise RuntimeError("text-to-speech provider is not connected")
        return self.text_to_speech.synthesize(speech)

    def verify_speaker(self, audio: VoiceInput, expected_subject: str) -> bool:
        if self.speaker_verifier is None:
            return False
        return self.speaker_verifier.verify(audio, expected_subject)



class VoiceProviderUnavailable(RuntimeError):
    pass


class ElevenLabsTextToSpeechProvider:
    """Synchronous ElevenLabs TTS adapter; voice identity is configured, not hardcoded."""

    def __init__(
        self,
        *,
        api_key_env: str = "ELEVENLABS_API_KEY",
        voice_id_env: str = "RUNE_ELEVENLABS_VOICE_ID",
        model_id_env: str = "RUNE_ELEVENLABS_MODEL_ID",
        output_format: str = "mp3_44100_128",
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key_env = api_key_env
        self.voice_id_env = voice_id_env
        self.model_id_env = model_id_env
        self.output_format = output_format
        self.timeout = timeout
        self.transport = transport

    def synthesize(self, speech: Speech) -> bytes:
        text = speech.text.strip()
        if not text:
            raise ValueError("speech text cannot be empty")
        if len(text) > 1000:
            raise ValueError("interactive RUNE speech is limited to 1000 characters per request")
        api_key = os.getenv(self.api_key_env)
        voice_id = speech.voice or os.getenv(self.voice_id_env)
        model_id = os.getenv(self.model_id_env, "eleven_flash_v2_5")
        if not api_key:
            raise VoiceProviderUnavailable("ElevenLabs API key is not configured")
        if not voice_id:
            raise VoiceProviderUnavailable("RUNE ElevenLabs voice ID is not configured")
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    params={"output_format": self.output_format},
                    headers={
                        "xi-api-key": api_key,
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                    },
                    json={"text": text, "model_id": model_id},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise VoiceProviderUnavailable("ElevenLabs speech synthesis request failed") from exc
        if not response.content:
            raise VoiceProviderUnavailable("ElevenLabs returned an empty audio response")
        return response.content



def configured_voice_pipeline() -> VoicePipeline:
    """Connect TTS only when its server-side credentials and voice ID exist."""
    if os.getenv("ELEVENLABS_API_KEY") and os.getenv("RUNE_ELEVENLABS_VOICE_ID"):
        return VoicePipeline(text_to_speech=ElevenLabsTextToSpeechProvider())
    return VoicePipeline()

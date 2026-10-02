from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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

    No microphone, cloud speech service, wake-word engine, or TTS vendor is
    connected here. Those adapters plug into these contracts later.
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

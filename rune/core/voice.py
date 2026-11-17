from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import os
import sqlite3
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import httpx


@dataclass(frozen=True)
class VoiceInput:
    audio: bytes
    sample_rate: int
    channels: int = 1
    audio_format: str = "wav"


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




class VoiceBudgetExceeded(RuntimeError):
    pass


class VoiceUsageLedger:
    """Conservative monthly character budget for billable TTS requests."""

    def __init__(
        self,
        path: str = "data/rune-voice-usage.db",
        monthly_limit: int = 10000,
    ) -> None:
        if monthly_limit < 1:
            raise ValueError("voice monthly character limit must be positive")
        self.monthly_limit = monthly_limit
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
        self.lock = threading.RLock()
        self.db.execute(
            "create table if not exists voice_usage (month text primary key, characters integer not null)"
        )
        self.db.commit()

    @staticmethod
    def month_key() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def reserve(self, characters: int) -> None:
        if characters < 1:
            raise ValueError("character reservation must be positive")
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                row = self.db.execute(
                    "select characters from voice_usage where month=?",
                    (self.month_key(),),
                ).fetchone()
                spent = int(row[0]) if row else 0
                if spent + characters > self.monthly_limit:
                    raise VoiceBudgetExceeded("monthly ElevenLabs character budget reached")
                self.db.execute(
                    "insert into voice_usage(month,characters) values(?,?) "
                    "on conflict(month) do update set characters=excluded.characters",
                    (self.month_key(), spent + characters),
                )
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

    def spent(self) -> int:
        with self.lock:
            row = self.db.execute(
                "select characters from voice_usage where month=?",
                (self.month_key(),),
            ).fetchone()
            return int(row[0]) if row else 0

    def close(self) -> None:
        with self.lock:
            self.db.close()


class OpenAISpeechToTextProvider:
    """OpenAI file transcription adapter for completed speech utterances."""

    _FORMATS = {
        "wav": ("audio/wav", "wav"),
        "mp3": ("audio/mpeg", "mp3"),
        "m4a": ("audio/mp4", "m4a"),
        "ogg": ("audio/ogg", "ogg"),
        "webm": ("audio/webm", "webm"),
        "flac": ("audio/flac", "flac"),
    }

    def __init__(
        self,
        *,
        api_key_env: str = "RUNE_OPENAI_STT_API_KEY",
        model_id_env: str = "RUNE_OPENAI_STT_MODEL_ID",
        timeout: float = 45.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key_env = api_key_env
        self.model_id_env = model_id_env
        self.timeout = timeout
        self.transport = transport

    def transcribe(self, audio: VoiceInput) -> Transcript:
        if not audio.audio:
            raise ValueError("audio payload cannot be empty")
        if len(audio.audio) > 25 * 1024 * 1024:
            raise ValueError("audio payload exceeds the 25 MB transcription limit")
        audio_format = audio.audio_format.lower().lstrip(".")
        file_type = self._FORMATS.get(audio_format)
        if file_type is None:
            raise ValueError("unsupported audio format")
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise VoiceProviderUnavailable("OpenAI speech-to-text API key is not configured")
        model_id = os.getenv(self.model_id_env, "gpt-transcribe")
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    data={"model": model_id},
                    files={"file": (f"rune-utterance.{file_type[1]}", audio.audio, file_type[0])},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise VoiceProviderUnavailable("OpenAI speech transcription request failed") from exc
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise VoiceProviderUnavailable("OpenAI returned an empty transcript")
        return Transcript(text=text.strip())




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
        usage_ledger: VoiceUsageLedger | None = None,
    ) -> None:
        self.api_key_env = api_key_env
        self.voice_id_env = voice_id_env
        self.model_id_env = model_id_env
        self.output_format = output_format
        self.timeout = timeout
        self.transport = transport
        monthly_limit = int(os.getenv("RUNE_ELEVENLABS_MONTHLY_CHAR_LIMIT", "10000"))
        self.usage_ledger = usage_ledger or VoiceUsageLedger(
            os.getenv("RUNE_VOICE_USAGE_DB", "data/rune-voice-usage.db"),
            monthly_limit=monthly_limit,
        )

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
        self.usage_ledger.reserve(len(text))
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
    speech_to_text = None
    if os.getenv("RUNE_OPENAI_STT_API_KEY"):
        speech_to_text = OpenAISpeechToTextProvider()
    text_to_speech = None
    if os.getenv("ELEVENLABS_API_KEY") and os.getenv("RUNE_ELEVENLABS_VOICE_ID"):
        text_to_speech = ElevenLabsTextToSpeechProvider()
    return VoicePipeline(speech_to_text=speech_to_text, text_to_speech=text_to_speech)



class VoiceSessionState(str, Enum):
    STANDBY = "standby"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    WAITING_CONFIRMATION = "waiting_confirmation"


class VoiceSessionController:
    """Deterministic voice-session state machine; background jobs are independent."""

    def __init__(self, inactivity_seconds: int = 120, confirmation_seconds: int = 15) -> None:
        if inactivity_seconds < 1 or confirmation_seconds < 1:
            raise ValueError("voice session timeouts must be positive")
        self.inactivity_seconds = inactivity_seconds
        self.confirmation_seconds = confirmation_seconds
        self.state = VoiceSessionState.STANDBY
        self.last_activity_at: float | None = None
        self.confirmation_deadline: float | None = None

    def wake_detected(self, now: float) -> None:
        self.state = VoiceSessionState.LISTENING
        self.last_activity_at = now
        self.confirmation_deadline = None

    def user_activity(self, now: float) -> None:
        if self.state == VoiceSessionState.STANDBY:
            return
        self.last_activity_at = now
        self.confirmation_deadline = None
        self.state = VoiceSessionState.LISTENING

    def processing_started(self, now: float) -> None:
        self.user_activity(now)
        if self.state != VoiceSessionState.STANDBY:
            self.state = VoiceSessionState.PROCESSING

    def speech_started(self, now: float) -> None:
        if self.state == VoiceSessionState.STANDBY:
            return
        self.last_activity_at = now
        self.state = VoiceSessionState.SPEAKING

    def speech_finished(self, now: float) -> None:
        if self.state == VoiceSessionState.SPEAKING:
            self.last_activity_at = now
            self.state = VoiceSessionState.LISTENING

    def interrupt(self, now: float) -> None:
        # Stops current speech playback only. It has no access to task execution.
        if self.state != VoiceSessionState.STANDBY:
            self.last_activity_at = now
            self.confirmation_deadline = None
            self.state = VoiceSessionState.LISTENING

    def tick(self, now: float) -> str | None:
        if self.state == VoiceSessionState.LISTENING and self.last_activity_at is not None:
            if now - self.last_activity_at >= self.inactivity_seconds:
                self.state = VoiceSessionState.WAITING_CONFIRMATION
                self.confirmation_deadline = now + self.confirmation_seconds
                return "You still there, or are we good?"
        elif self.state == VoiceSessionState.WAITING_CONFIRMATION:
            if self.confirmation_deadline is not None and now >= self.confirmation_deadline:
                self.close()
        return None

    def confirmation_prompted(self, now: float) -> None:
        if self.state == VoiceSessionState.WAITING_CONFIRMATION:
            self.confirmation_deadline = now + self.confirmation_seconds

    def answer_confirmation(self, continue_session: bool, now: float) -> None:
        if self.state != VoiceSessionState.WAITING_CONFIRMATION:
            return
        if continue_session:
            self.user_activity(now)
        else:
            self.close()

    def close(self) -> None:
        self.state = VoiceSessionState.STANDBY
        self.last_activity_at = None
        self.confirmation_deadline = None

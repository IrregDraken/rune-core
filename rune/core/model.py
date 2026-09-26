from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelResponse:
    content: str
    confidence: float = 0.0


class ModelProvider(Protocol):
    def respond(self, prompt: str) -> ModelResponse: ...


class DeterministicModel:
    """Development provider used until a real model adapter is connected."""

    def respond(self, prompt: str) -> ModelResponse:
        return ModelResponse(
            content=f"Model adapter received: {prompt}",
            confidence=1.0,
        )

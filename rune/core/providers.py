from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import httpx

from .model import ModelResponse, ModelProvider


class BudgetExceeded(RuntimeError):
    pass


class ProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    model: str
    api_key_env: str
    input_usd_per_million: float
    output_usd_per_million: float
    base_url: str | None = None
    max_output_tokens: int = 800


@dataclass(frozen=True)
class ProviderUsage:
    input_tokens: int
    output_tokens: int
    cost_usd: float


class TextProvider(Protocol):
    config: ProviderConfig
    def generate(self, prompt: str) -> tuple[str, ProviderUsage]: ...


class OpenAIChatProvider:
    def __init__(self, config: ProviderConfig, timeout: float = 45.0) -> None:
        self.config, self.timeout = config, timeout

    def generate(self, prompt: str) -> tuple[str, ProviderUsage]:
        key = os.getenv(self.config.api_key_env)
        if not key:
            raise ProviderUnavailable(f"{self.config.name} API key is not configured")
        url = (self.config.base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        try:
            response = httpx.post(url, headers={"Authorization": f"Bearer {key}"},
                json={"model": self.config.model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": self.config.max_output_tokens}, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderUnavailable(f"{self.config.name} request failed") from exc
        return text, _usage(self.config, usage)


class AnthropicMessagesProvider:
    def __init__(self, config: ProviderConfig, timeout: float = 45.0) -> None:
        self.config, self.timeout = config, timeout

    def generate(self, prompt: str) -> tuple[str, ProviderUsage]:
        key = os.getenv(self.config.api_key_env)
        if not key:
            raise ProviderUnavailable(f"{self.config.name} API key is not configured")
        url = (self.config.base_url or "https://api.anthropic.com").rstrip("/") + "/v1/messages"
        try:
            response = httpx.post(url, headers={
                "x-api-key": key, "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }, json={"model": self.config.model, "max_tokens": self.config.max_output_tokens,
                    "messages": [{"role": "user", "content": prompt}]}, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            text = "".join(part.get("text", "") for part in data.get("content", [])
                           if part.get("type") == "text")
            usage = data.get("usage", {})
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise ProviderUnavailable(f"{self.config.name} request failed") from exc
        return text, _usage(self.config, usage)


def _usage(config: ProviderConfig, raw: dict) -> ProviderUsage:
    input_tokens = int(raw.get("prompt_tokens", raw.get("input_tokens", 0)) or 0)
    output_tokens = int(raw.get("completion_tokens", raw.get("output_tokens", 0)) or 0)
    cost = (input_tokens * config.input_usd_per_million
            + output_tokens * config.output_usd_per_million) / 1_000_000
    return ProviderUsage(input_tokens, output_tokens, cost)


class UsageLedger:
    """Persistent monthly budget ledger; pricing must be configured from provider rates."""

    def __init__(self, path: str = "data/rune-usage.db", monthly_limit_usd: float = 33.0) -> None:
        if monthly_limit_usd <= 0:
            raise ValueError("monthly budget must be positive")
        self.monthly_limit_usd = monthly_limit_usd
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("""create table if not exists provider_usage (
            month text not null, provider text not null, input_tokens integer not null,
            output_tokens integer not null, cost_usd real not null,
            created_at text not null default current_timestamp)""")
        self.db.commit()

    @staticmethod
    def month_key() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def spent(self) -> float:
        row = self.db.execute("select coalesce(sum(cost_usd),0) from provider_usage where month=?",
                              (self.month_key(),)).fetchone()
        return float(row[0] or 0)

    def record(self, provider: str, usage: ProviderUsage) -> None:
        if self.spent() + usage.cost_usd > self.monthly_limit_usd:
            raise BudgetExceeded("monthly model API budget would be exceeded")
        self.db.execute("insert into provider_usage(month,provider,input_tokens,output_tokens,cost_usd) values(?,?,?,?,?)",
                        (self.month_key(), provider, usage.input_tokens, usage.output_tokens, usage.cost_usd))
        self.db.commit()

    def close(self) -> None:
        self.db.close()


class RoutedModelProvider(ModelProvider):
    """One RUNE identity with ordered, interchangeable inference providers."""

    def __init__(self, providers: list[TextProvider], ledger: UsageLedger) -> None:
        if not providers:
            raise ValueError("at least one model provider is required")
        self.providers, self.ledger = providers, ledger
        self.last_provider: str | None = None

    def respond(self, prompt: str) -> ModelResponse:
        failures: list[str] = []
        for provider in self.providers:
            try:
                text, usage = provider.generate(prompt)
                self.ledger.record(provider.config.name, usage)
                self.last_provider = provider.config.name
                return ModelResponse(content=text, confidence=0.85)
            except BudgetExceeded:
                raise
            except ProviderUnavailable as exc:
                failures.append(str(exc))
        raise ProviderUnavailable("; ".join(failures) or "no model provider available")

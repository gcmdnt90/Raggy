"""LLM Router — routes requests to the selected provider."""

from __future__ import annotations

import logging
from typing import Iterator

from app.llm.base import (
    LLMBudgetExceededError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMError,
)
from app.utils.token_budget import (
    can_spend,
    estimate_messages_tokens,
    estimate_text_tokens,
    record_usage,
    usage_from_provider_usage,
)

logger = logging.getLogger(__name__)
DEFAULT_MAX_TOKENS = 1500
HARD_MAX_TOKENS = 4000

# Lazy import paths to avoid errors if an SDK isn't installed
_PROVIDER_PATHS: dict[str, tuple[str, str]] = {
    "anthropic": ("app.llm.providers.anthropic", "AnthropicProvider"),
    "openai":    ("app.llm.providers.openai_provider", "OpenAIProvider"),
    "google":    ("app.llm.providers.google", "GoogleProvider"),
    "ollama":    ("app.llm.providers.ollama", "OllamaProvider"),
}


def _load_provider_class(name: str) -> type[LLMProvider]:
    """Dynamically load the requested provider class."""
    if name not in _PROVIDER_PATHS:
        available = ", ".join(sorted(_PROVIDER_PATHS))
        raise LLMError(
            f"Provider '{name}' not supported. "
            f"Available providers: {available}"
        )

    module_path, class_name = _PROVIDER_PATHS[name]

    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class LLMRouter:
    """Router that delegates LLM calls to the configured provider.

    Example:
        router = LLMRouter("ollama", model="gemma3:4b")
        response = router.generate([LLMMessage("user", "Hello!")])

    Switch provider at runtime:
        router.set_provider("anthropic", api_key="sk-...")
    """

    PROVIDERS: dict[str, str] = {k: v[1] for k, v in _PROVIDER_PATHS.items()}

    def __init__(self, provider: str, **kwargs) -> None:
        self._provider_name = provider
        self._kwargs = kwargs
        self._provider: LLMProvider = self._create_provider(provider, **kwargs)

    @staticmethod
    def _create_provider(provider: str, **kwargs) -> LLMProvider:
        cls = _load_provider_class(provider)
        return cls(**kwargs)

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @staticmethod
    def _effective_max_tokens(max_tokens: int | None) -> int:
        requested = DEFAULT_MAX_TOKENS if max_tokens is None else int(max_tokens)
        return max(1, min(requested, HARD_MAX_TOKENS))

    @staticmethod
    def _ensure_budget(messages: list[LLMMessage], max_tokens: int) -> None:
        planned = estimate_messages_tokens(messages) + max_tokens
        if not can_spend(planned):
            raise LLMBudgetExceededError("Daily token budget reached, try again tomorrow.")

    def set_provider(self, provider: str, **kwargs) -> None:
        logger.info("Switching provider: %s -> %s", self._provider_name, provider)
        self._provider = self._create_provider(provider, **kwargs)
        self._provider_name = provider
        self._kwargs = kwargs

    @classmethod
    def list_providers(cls) -> list[str]:
        return sorted(_PROVIDER_PATHS.keys())

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        effective_max_tokens = self._effective_max_tokens(max_tokens)
        self._ensure_budget(messages, effective_max_tokens)
        response = self._provider.generate(
            messages, model=model, temperature=temperature, max_tokens=effective_max_tokens,
        )
        actual_usage = usage_from_provider_usage(response.usage)
        fallback_usage = estimate_messages_tokens(messages) + estimate_text_tokens(response.content)
        record_usage(actual_usage or fallback_usage)
        return response

    def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        effective_max_tokens = self._effective_max_tokens(max_tokens)
        self._ensure_budget(messages, effective_max_tokens)
        chunks: list[str] = []
        try:
            for chunk in self._provider.generate_stream(
                messages, model=model, temperature=temperature, max_tokens=effective_max_tokens,
            ):
                chunks.append(chunk)
                yield chunk
        finally:
            record_usage(
                estimate_messages_tokens(messages)
                + estimate_text_tokens("".join(chunks))
            )

    def embed(
        self, texts: list[str], *, model: str | None = None
    ) -> list[list[float]]:
        return self._provider.embed(texts, model=model)

    def test_connection(self) -> bool:
        return self._provider.test_connection()

    def available_models(self) -> list[str]:
        return self._provider.available_models()

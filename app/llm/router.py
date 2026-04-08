"""LLM Router — routes requests to the selected provider."""

from __future__ import annotations

import logging
from typing import Iterator

from app.llm.base import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    LLMError,
)

logger = logging.getLogger(__name__)

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
        return self._provider.generate(
            messages, model=model, temperature=temperature, max_tokens=max_tokens,
        )

    def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        return self._provider.generate_stream(
            messages, model=model, temperature=temperature, max_tokens=max_tokens,
        )

    def embed(
        self, texts: list[str], *, model: str | None = None
    ) -> list[list[float]]:
        return self._provider.embed(texts, model=model)

    def test_connection(self) -> bool:
        return self._provider.test_connection()

    def available_models(self) -> list[str]:
        return self._provider.available_models()

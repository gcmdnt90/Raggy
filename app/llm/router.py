"""LLM Router — routes requests to the selected provider."""

from __future__ import annotations

import logging
from collections.abc import Iterator

from app.llm.base import (
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    ProviderRequest,
)
from app.utils.token_budget import (
    estimate_messages_tokens,
    estimate_text_tokens,
    record_usage,
    usage_from_provider_usage,
)

logger = logging.getLogger(__name__)
DEFAULT_MAX_TOKENS = 1500

# `HARD_MAX_TOKENS = 4000` used to clamp every request here, and
# `_ensure_budget` used to refuse a call once a daily estimate was spent. Both
# are gone — see ADR 0005 and docs/specs/usage-and-headroom.md.
#
# They were inherited Raggy safety rails, written for an application that might
# be handed to somebody else. Banco is run by the person who owns the keys, in
# front of a room, on a clock. A ceiling that silently shortens an answer and a
# refusal based on a *character-count estimate* both fail in the same direction:
# the demonstration stops or degrades for a reason nobody in the room can see.
#
# The ceiling was also arithmetically incompatible with what D2 teaches.
# Anthropic requires `1024 <= thinking.budget_tokens < max_tokens`, so a 4000
# clamp left under 3000 tokens for an answer at the smallest legal budget and
# made every larger one unreachable.
#
# Usage is still *measured* on every call — `record_usage` below — because ADR
# 0005 keeps measurement and removes only the refusal. A figure shown as a
# measurement was measured; nothing here estimates in order to forbid.

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
        """What the caller asked for, floored at 1. No ceiling — see above."""
        requested = DEFAULT_MAX_TOKENS if max_tokens is None else int(max_tokens)
        return max(1, requested)

    def set_provider(self, provider: str, **kwargs) -> None:
        logger.info("Switching provider: %s -> %s", self._provider_name, provider)
        self._provider = self._create_provider(provider, **kwargs)
        self._provider_name = provider
        self._kwargs = kwargs

    @classmethod
    def list_providers(cls) -> list[str]:
        return sorted(_PROVIDER_PATHS.keys())

    def prepare(
        self,
        messages: list[LLMMessage],
        params: dict | None = None,
        *,
        model: str | None = None,
    ) -> ProviderRequest:
        """Build the request without sending it.

        Exposed on the router so a caller that needs to know what will be sent
        *before* the stream opens — the runner, laying out panes — does not have
        to reach past it to the provider.
        """
        return self._provider.prepare(messages, params, model=model)

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        params: dict | None = None,
        request: ProviderRequest | None = None,
    ) -> LLMResponse:
        response = self._provider.generate(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=(
                self._effective_max_tokens(max_tokens) if max_tokens is not None else None
            ),
            params=params,
            request=request,
        )
        actual_usage = usage_from_provider_usage(response.usage)
        fallback_usage = estimate_messages_tokens(messages) + estimate_text_tokens(response.content)
        # An estimate is recorded only when the provider reported nothing. ADR
        # 0005: a figure shown as a measurement was measured, so whoever renders
        # this has to be able to tell the two apart — which is why the actual
        # value is preferred here rather than averaged with the estimate.
        record_usage(actual_usage or fallback_usage)
        return response

    def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        params: dict | None = None,
        request: ProviderRequest | None = None,
    ) -> Iterator[str]:
        chunks: list[str] = []
        try:
            for chunk in self._provider.generate_stream(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=(
                    self._effective_max_tokens(max_tokens)
                    if max_tokens is not None else None
                ),
                params=params,
                request=request,
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

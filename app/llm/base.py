"""Base classes and interfaces for Raggy LLM providers."""

from __future__ import annotations

import time
import logging
import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Iterator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class LLMMessage:
    """Single message in a conversation."""
    role: str          # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    provider: str
    usage: dict[str, int] | None = None


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class LLMError(Exception):
    """Base exception for LLM errors."""


class LLMAuthenticationError(LLMError):
    """Missing or invalid API key."""


class LLMConnectionError(LLMError):
    """Cannot reach the provider."""


class LLMModelNotFoundError(LLMError):
    """Requested model not available."""


class LLMTimeoutError(LLMError):
    """Timeout while calling the provider."""


class LLMRateLimitError(LLMError):
    """Rate limit reached — used internally for retry."""


# ---------------------------------------------------------------------------
# Retry decorator with exponential backoff
# ---------------------------------------------------------------------------

def retry_with_backoff(max_attempts: int = 3, base_delay: float = 1.0):
    """Decorator: retry on rate-limit with exponential backoff."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except LLMRateLimitError as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "Rate limit hit (attempt %d/%d). Retrying in %.1f s…",
                            attempt, max_attempts, delay,
                        )
                        time.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Abstract base class for providers
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Common interface for all supported LLM providers."""

    provider_name: str = ""
    default_model: str = ""

    def __init__(
        self,
        api_key: str = "",
        model: str | None = None,
        timeout: int = 120,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs,
    ) -> None:
        self.api_key = api_key
        self.model = model or self.default_model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def available_models(self) -> list[str]:
        """Return the list of available models."""
        ...

    @abstractmethod
    def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a complete response (non-streaming)."""
        ...

    @abstractmethod
    def generate_stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Generate a streaming response, yielding text chunks."""
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify the provider is reachable and credentials are valid."""
        ...

    @abstractmethod
    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        """Return embeddings for a list of texts."""
        ...

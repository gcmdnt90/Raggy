"""Base classes and interfaces for Raggy LLM providers."""

from __future__ import annotations

import functools
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

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
# Banco's parameter vocabulary and the prepared request
# ---------------------------------------------------------------------------

#: The four names that may cross the boundary into a provider. Each adapter
#: translates them into whatever that vendor calls the same thing, and reports
#: the ones it could not carry. Nothing else is a parameter.
#: See docs/specs/model-control.md §3.
PARAM_NAMES = frozenset({"temperature", "max_tokens", "system", "think"})

#: Values `think` may take, besides an integer token budget. One field with
#: three shapes on purpose: the vendors do not agree, and D2's mechanism is
#: that deliberation is a *budget* and not a switch.
THINK_LEVELS = ("low", "medium", "high", "max")


class UnknownParameterError(LLMError):
    """A parameter name outside `PARAM_NAMES` reached a provider."""


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    """A request built but not yet sent, and an account of what happened to it.

    Built by `LLMProvider.prepare`, which makes no network call, so every
    provider's parameter handling is unit-testable without a key. That is how
    `anthropic==1.2.0` dropping `temperature` from `Messages.create` should
    have been caught.

    `sent` and `dropped` are derived from `payload` itself, never from a
    capability table, because the projected surface displays them: a parameter
    shown as sent must have been in the request, and one that was discarded
    must be shown as discarded rather than as a value. PROJECT.md invariant:
    *a parameter is displayed only if the request carried it*.

    `payload` never leaves the process. `sent` does, after `redact()`.
    """

    model: str
    #: Exactly what goes to the SDK. Not serialised to any surface.
    payload: dict
    #: Banco-vocabulary parameters that reached `payload`.
    sent: dict
    #: Banco parameter -> an i18n key saying why it did not. A key rather than
    #: prose because the reason is rendered on a projected surface and Banco
    #: speaks two languages (AGENTS.md rule 9).
    dropped: dict[str, str]


def validate_params(params: dict | None) -> dict:
    """Reject anything outside the vocabulary, and normalise `think`.

    Raised rather than ignored: a misspelled parameter that is silently
    discarded is a demonstration that runs, looks correct and teaches nothing —
    which is the whole failure mode this layer exists to end.
    """
    values = dict(params or {})
    unknown = sorted(set(values) - PARAM_NAMES)
    if unknown:
        raise UnknownParameterError(
            f"not Banco parameters: {', '.join(unknown)}. "
            f"Known: {', '.join(sorted(PARAM_NAMES))}"
        )

    think = values.get("think")
    if think is not None and not isinstance(think, bool):
        if isinstance(think, int):
            if think < 1:
                raise UnknownParameterError(
                    f"think budget must be a positive number of tokens, got {think}"
                )
        elif isinstance(think, str):
            if think not in THINK_LEVELS:
                raise UnknownParameterError(
                    f"think level {think!r} is not one of: {', '.join(THINK_LEVELS)}"
                )
        else:
            raise UnknownParameterError(
                f"think must be false, a level, or a token budget; got {type(think).__name__}"
            )
    return values


def split_system(
    messages: list[LLMMessage], system_param: str | None = None
) -> tuple[str | None, list[LLMMessage]]:
    """Separate system text from the conversation, appending the `system` param.

    One implementation for all four providers, because "the system prompt as
    sent" is displayed to the room (PROJECT.md objective 2) and four slightly
    different joins would make that display provider-dependent.

    The `system` parameter comes last so that a standing instruction configured
    for the run is read after anything the conversation carried — which is the
    order D4 teaches, where the house rules are written once and reread on
    every request.
    """
    parts: list[str] = []
    rest: list[LLMMessage] = []
    for message in messages:
        if message.role == "system":
            parts.append(message.content)
        else:
            rest.append(message)
    if system_param:
        parts.append(system_param)
    return ("\n\n".join(p for p in parts if p).strip() or None), rest


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
        max_tokens: int = 1500,
        **kwargs,
    ) -> None:
        self.api_key = api_key
        self.model = model or self.default_model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

    #: Extra attributes `prepare` reads that `__init__` would normally set.
    #: Overridden by providers that need more than the three below.
    INSPECTION_DEFAULTS: dict = {}

    @classmethod
    def for_inspection(cls, model: str, *, temperature: float = 0.3,
                       max_tokens: int = 1500) -> LLMProvider:
        """An instance that can `prepare` and nothing else.

        Built without a client and without a credential, because pre-flight has
        to answer "would this model actually apply the parameter this demo
        teaches" for every configured source, on page load, without spending a
        call. `prepare` touches no client, so an instance carrying only the
        attributes it reads is a complete answer.

        It must never be used to call: there is no client on it, and that is
        deliberate rather than incidental.
        """
        provider = object.__new__(cls)
        provider.api_key = ""
        provider.model = model
        provider.timeout = 120
        provider.temperature = temperature
        provider.max_tokens = max_tokens
        for name, value in cls.INSPECTION_DEFAULTS.items():
            setattr(provider, name, value)
        return provider

    def resolve_params(
        self,
        params: dict | None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Fold the legacy keyword arguments into Banco's parameter vocabulary.

        `generate(temperature=…, max_tokens=…)` predates the vocabulary and is
        still how the RAG pipeline and pre-flight call a provider. Rather than
        two parameter paths through each adapter there is one: the keywords
        become entries in `params` and every provider reads only `params`.

        `params` wins where both are given, because `params` is what a run
        block and a session profile speak (docs/specs/model-control.md §2).
        """
        merged = dict(params or {})
        if temperature is not None:
            merged.setdefault("temperature", temperature)
        if max_tokens is not None:
            merged.setdefault("max_tokens", max_tokens)
        merged.setdefault("temperature", self.temperature)
        merged.setdefault("max_tokens", self.max_tokens)
        return validate_params(merged)

    @abstractmethod
    def prepare(
        self,
        messages: list[LLMMessage],
        params: dict | None = None,
        *,
        model: str | None = None,
    ) -> ProviderRequest:
        """Build the request without sending it, and say what survived.

        Makes no network call and touches no credential, so every adapter's
        parameter handling can be tested without a key. The caller reads
        `sent` and `dropped` *before* the stream starts, which is what lets the
        harness label its panes truthfully as it lays them out.
        """
        ...

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
        params: dict | None = None,
        request: ProviderRequest | None = None,
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
        params: dict | None = None,
        request: ProviderRequest | None = None,
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

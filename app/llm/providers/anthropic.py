"""Anthropic (Claude) provider for Raggy."""

from __future__ import annotations

import logging
import re
from typing import Iterator

from app.llm.base import (
    LLMMessage, LLMProvider, LLMResponse,
    LLMAuthenticationError, LLMConnectionError,
    LLMModelNotFoundError, LLMRateLimitError,
    LLMTimeoutError, retry_with_backoff,
)
from app.llm.providers import model_catalog

logger = logging.getLogger(__name__)


def _supports_temperature(model: str) -> bool:
    """Return whether ``model`` accepts a non-default temperature.

    Anthropic removed sampling parameters from models released after Claude
    Opus 4.6. Canonical model IDs from the 4.6 generation onward put the
    family before the numeric version (for example, ``claude-opus-4-8``).
    Older IDs use a different shape and continue to support temperature.
    """
    match = re.match(r"^claude-([a-z]+)-(\d+)(?:-(\d+))?(?:-|$)", model)
    if not match:
        return True

    family, major_text, minor_text = match.groups()
    version = (int(major_text), int(minor_text or 0))
    return version < (5, 0) and not (family == "opus" and version > (4, 6))


class AnthropicProvider(LLMProvider):
    """Provider for the Anthropic Messages API."""

    provider_name: str = "anthropic"
    default_model: str = "claude-sonnet-4-6"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if not self.api_key:
            raise LLMAuthenticationError(
                "Anthropic API key missing. Set ANTHROPIC_API_KEY in .env."
            )
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError("Package 'anthropic' not installed. Run: pip install anthropic") from exc
        self._client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)

    @staticmethod
    def _split_messages(messages: list[LLMMessage]) -> tuple[str | None, list[dict[str, str]]]:
        system_text: str | None = None
        chat_msgs: list[dict[str, str]] = []
        for msg in messages:
            if msg.role == "system":
                system_text = f"{system_text}\n{msg.content}" if system_text else msg.content
            else:
                chat_msgs.append({"role": msg.role, "content": msg.content})
        return system_text, chat_msgs

    def _fetch_models(self) -> list[str]:
        """Query the Anthropic API for the currently available Claude models."""
        page = self._client.models.list(limit=1000)
        return [m.id for m in page.data if m.id.startswith("claude")]

    def available_models(self) -> list[str]:
        """Live model list from the API, with a static fallback when offline."""
        return model_catalog.discover(
            self.provider_name,
            self._fetch_models,
            cache_key=model_catalog.credential_cache_key(self.api_key),
        )

    @retry_with_backoff(max_attempts=3)
    def generate(self, messages: list[LLMMessage], *, model: str | None = None,
                 temperature: float | None = None, max_tokens: int | None = None) -> LLMResponse:
        import anthropic as _anthropic
        target_model = model or self.model
        system_text, chat_msgs = self._split_messages(messages)
        kwargs: dict = {
            "model": target_model, "messages": chat_msgs,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if _supports_temperature(target_model):
            kwargs["temperature"] = temperature if temperature is not None else self.temperature
        if system_text:
            kwargs["system"] = system_text
        try:
            response = self._client.messages.create(**kwargs)
        except _anthropic.AuthenticationError as exc:
            raise LLMAuthenticationError(str(exc)) from exc
        except _anthropic.RateLimitError as exc:
            raise LLMRateLimitError(str(exc)) from exc
        except _anthropic.NotFoundError as exc:
            raise LLMModelNotFoundError(f"Model '{target_model}' not found: {exc}") from exc
        except _anthropic.APITimeoutError as exc:
            raise LLMTimeoutError(str(exc)) from exc
        except _anthropic.APIConnectionError as exc:
            raise LLMConnectionError(str(exc)) from exc
        content = response.content[0].text if response.content else ""
        usage = ({"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
                 if response.usage else None)
        return LLMResponse(content=content, model=response.model, provider=self.provider_name, usage=usage)

    @retry_with_backoff(max_attempts=3)
    def generate_stream(self, messages: list[LLMMessage], *, model: str | None = None,
                        temperature: float | None = None, max_tokens: int | None = None) -> Iterator[str]:
        import anthropic as _anthropic
        target_model = model or self.model
        system_text, chat_msgs = self._split_messages(messages)
        kwargs: dict = {
            "model": target_model, "messages": chat_msgs,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if _supports_temperature(target_model):
            kwargs["temperature"] = temperature if temperature is not None else self.temperature
        if system_text:
            kwargs["system"] = system_text
        try:
            with self._client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield text
        except _anthropic.AuthenticationError as exc:
            raise LLMAuthenticationError(str(exc)) from exc
        except _anthropic.RateLimitError as exc:
            raise LLMRateLimitError(str(exc)) from exc
        except _anthropic.NotFoundError as exc:
            raise LLMModelNotFoundError(f"Model '{target_model}' not found: {exc}") from exc
        except _anthropic.APITimeoutError as exc:
            raise LLMTimeoutError(str(exc)) from exc
        except _anthropic.APIConnectionError as exc:
            raise LLMConnectionError(str(exc)) from exc

    def test_connection(self) -> bool:
        try:
            self.generate([LLMMessage(role="user", content="ping")], max_tokens=16)
            return True
        except Exception as exc:
            logger.warning("Anthropic connection test failed (%s)", type(exc).__name__)
            return False

    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        raise NotImplementedError("Anthropic does not provide an embedding endpoint. Use OpenAI, Google, or a local model.")

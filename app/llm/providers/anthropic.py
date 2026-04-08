"""Anthropic (Claude) provider for Raggy."""

from __future__ import annotations

import logging
from typing import Iterator

from app.llm.base import (
    LLMMessage, LLMProvider, LLMResponse,
    LLMAuthenticationError, LLMConnectionError,
    LLMModelNotFoundError, LLMRateLimitError,
    LLMTimeoutError, retry_with_backoff,
)

logger = logging.getLogger(__name__)

_MODELS: list[str] = [
    "claude-sonnet-4-20250514",
    "claude-opus-4-6",
    "claude-haiku-4-5-20251001",
]


class AnthropicProvider(LLMProvider):
    """Provider for the Anthropic Messages API."""

    provider_name: str = "anthropic"
    default_model: str = "claude-sonnet-4-20250514"

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

    def available_models(self) -> list[str]:
        return list(_MODELS)

    @retry_with_backoff(max_attempts=3)
    def generate(self, messages: list[LLMMessage], *, model: str | None = None,
                 temperature: float | None = None, max_tokens: int | None = None) -> LLMResponse:
        import anthropic as _anthropic
        target_model = model or self.model
        system_text, chat_msgs = self._split_messages(messages)
        kwargs: dict = {
            "model": target_model, "messages": chat_msgs,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
        }
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
            "temperature": temperature if temperature is not None else self.temperature,
        }
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
        except Exception:
            logger.exception("Anthropic connection test failed")
            return False

    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        raise NotImplementedError("Anthropic does not provide an embedding endpoint. Use OpenAI, Google, or a local model.")

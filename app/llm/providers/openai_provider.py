"""OpenAI provider for Raggy."""

from __future__ import annotations

import logging
from typing import Iterator

from app.llm.base import (
    LLMMessage, LLMProvider, LLMResponse,
    LLMAuthenticationError, LLMConnectionError,
    LLMModelNotFoundError, LLMRateLimitError,
    LLMTimeoutError, retry_with_backoff,
)
from app.llm.providers import model_catalog

logger = logging.getLogger(__name__)

# Keep only chat/completion-capable models out of the full /models listing
# (which also includes embeddings, audio, image, moderation, etc.).
_CHAT_PREFIXES = ("gpt-", "o1", "o3", "o4", "chatgpt")
_NON_CHAT_MARKERS = (
    "embedding", "audio", "realtime", "transcribe", "tts",
    "whisper", "image", "dall-e", "moderation", "search", "instruct",
)


class OpenAIProvider(LLMProvider):
    """Provider for the OpenAI Chat Completions API."""

    provider_name: str = "openai"
    default_model: str = "gpt-4o-mini"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if not self.api_key:
            raise LLMAuthenticationError("OpenAI API key missing. Set OPENAI_API_KEY in .env.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("Package 'openai' not installed. Run: pip install openai") from exc
        self._client = OpenAI(api_key=self.api_key, timeout=self.timeout)

    def _fetch_models(self) -> list[str]:
        """Query the OpenAI API and keep only chat-capable models."""
        out: list[str] = []
        for m in self._client.models.list().data:
            mid = m.id
            if mid.startswith(_CHAT_PREFIXES) and not any(x in mid for x in _NON_CHAT_MARKERS):
                out.append(mid)
        return out

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
        from openai import AuthenticationError, RateLimitError, APITimeoutError, APIConnectionError, NotFoundError
        target_model = model or self.model
        oai_msgs = [{"role": m.role, "content": m.content} for m in messages]
        try:
            response = self._client.chat.completions.create(
                model=target_model, messages=oai_msgs,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature if temperature is not None else self.temperature,
            )
        except AuthenticationError as exc:
            raise LLMAuthenticationError(str(exc)) from exc
        except RateLimitError as exc:
            raise LLMRateLimitError(str(exc)) from exc
        except NotFoundError as exc:
            raise LLMModelNotFoundError(f"Model '{target_model}' not found: {exc}") from exc
        except APITimeoutError as exc:
            raise LLMTimeoutError(str(exc)) from exc
        except APIConnectionError as exc:
            raise LLMConnectionError(str(exc)) from exc
        choice = response.choices[0]
        usage = ({"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens,
                  "total_tokens": response.usage.total_tokens} if response.usage else None)
        return LLMResponse(content=choice.message.content or "", model=response.model,
                           provider=self.provider_name, usage=usage)

    @retry_with_backoff(max_attempts=3)
    def generate_stream(self, messages: list[LLMMessage], *, model: str | None = None,
                        temperature: float | None = None, max_tokens: int | None = None) -> Iterator[str]:
        from openai import AuthenticationError, RateLimitError, APITimeoutError, APIConnectionError, NotFoundError
        target_model = model or self.model
        oai_msgs = [{"role": m.role, "content": m.content} for m in messages]
        try:
            stream = self._client.chat.completions.create(
                model=target_model, messages=oai_msgs,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature if temperature is not None else self.temperature,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except AuthenticationError as exc:
            raise LLMAuthenticationError(str(exc)) from exc
        except RateLimitError as exc:
            raise LLMRateLimitError(str(exc)) from exc
        except NotFoundError as exc:
            raise LLMModelNotFoundError(f"Model '{target_model}' not found: {exc}") from exc
        except APITimeoutError as exc:
            raise LLMTimeoutError(str(exc)) from exc
        except APIConnectionError as exc:
            raise LLMConnectionError(str(exc)) from exc

    def test_connection(self) -> bool:
        try:
            self.generate([LLMMessage(role="user", content="ping")], max_tokens=16)
            return True
        except Exception as exc:
            logger.warning("OpenAI connection test failed (%s)", type(exc).__name__)
            return False

    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        response = self._client.embeddings.create(model=model or "text-embedding-3-small", input=texts)
        return [item.embedding for item in response.data]

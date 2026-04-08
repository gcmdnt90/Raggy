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

logger = logging.getLogger(__name__)

_MODELS: list[str] = ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini"]


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

    def available_models(self) -> list[str]:
        return list(_MODELS)

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
        except Exception:
            logger.exception("OpenAI connection test failed")
            return False

    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        response = self._client.embeddings.create(model=model or "text-embedding-3-small", input=texts)
        return [item.embedding for item in response.data]

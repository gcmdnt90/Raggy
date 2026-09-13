"""OpenAI provider for Raggy."""

from __future__ import annotations

import inspect
import logging
import re
from collections.abc import Iterator
from functools import lru_cache

from app.llm.base import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMMessage,
    LLMModelNotFoundError,
    LLMProvider,
    LLMRateLimitError,
    LLMResponse,
    LLMTimeoutError,
    ProviderRequest,
    retry_with_backoff,
    split_system,
)
from app.llm.providers import model_catalog

logger = logging.getLogger(__name__)

#: Model families that deliberate, and therefore take `reasoning_effort` rather
#: than a temperature. The pattern is advisory in exactly the way
#: docs/specs/model-control.md §4.3 describes a capability table: when it is
#: wrong the parameter is refused by the API and the pane says so, which is
#: recoverable. It is not consulted by anything that makes a claim on screen.
_REASONING_MODEL = re.compile(r"^(o\d|gpt-5|gpt-6)")

#: `reasoning_effort` accepts levels, not budgets. Taken from the vendor
#: documentation cited in docs/specs/model-control.md §4.2 and deliberately not
#: widened here: a level Banco invents is a level the API rejects.
_EFFORT_LEVELS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")


def _is_reasoning_model(model: str) -> bool:
    return bool(_REASONING_MODEL.match(model))


@lru_cache(maxsize=1)
def _completions_parameters() -> frozenset[str]:
    """What the installed SDK's `chat.completions.create` will actually accept.

    Inspected rather than assumed, for the reason the Anthropic adapter
    documents at length: this signature changes between releases of a library
    this project pins, and the cost of finding out at call time is a dead pane
    in front of a room. An inspection that fails returns the conservative set
    that every version of this endpoint has had.
    """
    try:
        from openai.resources.chat.completions import Completions

        return frozenset(inspect.signature(Completions.create).parameters)
    except Exception:  # noqa: BLE001 - fall back to what has always existed
        return frozenset({"model", "messages", "max_tokens", "temperature", "stream"})

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

    def prepare(self, messages: list[LLMMessage], params: dict | None = None, *,
                model: str | None = None) -> ProviderRequest:
        """Build a Chat Completions request.

        This resolves the open decision left in docs/specs/model-control.md
        §4.2. The spec offered two ways to make a reasoning model selectable
        from the console: add a Responses-API path, or keep reasoning models
        off the list until there is one. Neither is needed — the pinned SDK's
        `chat.completions.create` already takes `reasoning_effort` and
        `max_completion_tokens`, so a reasoning model is selectable on the
        endpoint Banco already uses. The signature is inspected rather than
        trusted, so an SDK that removes either one degrades to a reported drop
        instead of a TypeError.

        A reasoning model does not take a sampling temperature. That is a drop
        with a reason, not a silently ignored value: D1 is the temperature demo
        and a pane that claims a temperature it never sent would break it.
        """
        values = self.resolve_params(params)
        target_model = model or self.model
        accepted = _completions_parameters()
        reasoning = _is_reasoning_model(target_model)

        system_text, chat = split_system(messages, values.get("system"))
        conversation = ([{"role": "system", "content": system_text}] if system_text else [])
        conversation += [{"role": m.role, "content": m.content} for m in chat]

        payload: dict = {"model": target_model, "messages": conversation}
        sent: dict = {}
        dropped: dict[str, str] = {}
        if system_text:
            sent["system"] = system_text

        # ── generation ceiling ─────────────────────────────────────────────
        max_tokens = int(values["max_tokens"])
        ceiling_field = "max_completion_tokens" if (
            reasoning and "max_completion_tokens" in accepted
        ) else "max_tokens"
        if ceiling_field in accepted:
            payload[ceiling_field] = max_tokens
            sent["max_tokens"] = max_tokens
        else:
            dropped["max_tokens"] = "drop.max_tokens.sdk_lacks_parameter"

        # ── temperature ────────────────────────────────────────────────────
        temperature = values.get("temperature")
        if temperature is not None:
            if reasoning:
                dropped["temperature"] = "drop.temperature.reasoning_model"
            elif "temperature" not in accepted:
                dropped["temperature"] = "drop.temperature.sdk_lacks_parameter"
            else:
                payload["temperature"] = float(temperature)
                sent["temperature"] = float(temperature)

        # ── deliberation ───────────────────────────────────────────────────
        think = values.get("think")
        if think is not None:
            if not reasoning:
                dropped["think"] = "drop.think.model_does_not_deliberate"
            elif "reasoning_effort" not in accepted:
                dropped["think"] = "drop.think.sdk_lacks_parameter"
            elif think is False:
                # OpenAI expresses "do not deliberate" as an effort level, which
                # is a real value and therefore really sent.
                payload["reasoning_effort"] = "none"
                sent["think"] = False
            elif isinstance(think, str) and think in _EFFORT_LEVELS:
                payload["reasoning_effort"] = think
                sent["think"] = think
            elif isinstance(think, str):
                dropped["think"] = "drop.think.level_not_offered"
            else:
                # An integer budget. Not rounded to a level — see §3.
                dropped["think"] = "drop.think.openai_takes_a_level"

        return ProviderRequest(model=target_model, payload=payload, sent=sent, dropped=dropped)

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
                 temperature: float | None = None, max_tokens: int | None = None,
                 params: dict | None = None,
                 request: ProviderRequest | None = None) -> LLMResponse:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            NotFoundError,
            RateLimitError,
        )
        request = request or self.prepare(
            messages, self.resolve_params(params, temperature, max_tokens), model=model
        )
        target_model = request.model
        try:
            response = self._client.chat.completions.create(**request.payload)
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
                        temperature: float | None = None, max_tokens: int | None = None,
                        params: dict | None = None,
                        request: ProviderRequest | None = None) -> Iterator[str]:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            NotFoundError,
            RateLimitError,
        )
        request = request or self.prepare(
            messages, self.resolve_params(params, temperature, max_tokens), model=model
        )
        target_model = request.model
        try:
            stream = self._client.chat.completions.create(**request.payload, stream=True)
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

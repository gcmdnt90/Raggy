"""Anthropic (Claude) provider for Raggy."""

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

#: Anthropic's documented floor for `thinking.budget_tokens`. The API rejects
#: less, so a smaller budget is refused here — before the call, where the
#: reason can be shown — rather than turned into a 400 mid-demonstration.
MIN_THINKING_BUDGET = 1024


@lru_cache(maxsize=1)
def _sdk_accepts_temperature() -> bool:
    """Whether the installed SDK's ``Messages.create`` takes ``temperature``.

    Asked of the SDK rather than assumed, because this changed underneath
    Banco. ``anthropic==1.2.0`` — the version both locks pin — has no
    ``temperature`` parameter on ``Messages.create`` at all, and no ``**kwargs``
    to absorb one, so sending it raised

        TypeError: Messages.create() got an unexpected keyword argument 'temperature'

    before the request was ever made. Every Anthropic pane died on that, and
    pre-flight could only report "did not answer".

    Inspected rather than hard-coded so an SDK that brings the parameter back
    needs no edit here. Inspection that fails, or a wrapper that hides the
    signature, resolves to False — which is the safe direction: not sending a
    parameter costs a default temperature, sending an unsupported one costs the
    whole call.
    """
    try:
        from anthropic.resources.messages import Messages

        return "temperature" in inspect.signature(Messages.create).parameters
    except Exception:  # noqa: BLE001 - any failure here means "do not send it"
        return False


@lru_cache(maxsize=1)
def _sdk_accepts_thinking() -> bool:
    """Whether the installed SDK's ``Messages.create`` takes ``thinking``.

    Asked rather than assumed, for the same reason as `_sdk_accepts_temperature`
    and with the same failure in mind: the temperature parameter disappeared
    from this signature between two releases of a library this project pins, and
    nothing noticed until four panes died in rehearsal. `thinking` is the
    parameter D2 is built on, so it gets the same check.

    False resolves to "do not send it", which costs the deliberation budget and
    says so. Sending an unsupported keyword costs the whole call.
    """
    try:
        from anthropic.resources.messages import Messages

        return "thinking" in inspect.signature(Messages.create).parameters
    except Exception:  # noqa: BLE001 - any failure here means "do not send it"
        return False


def _supports_temperature(model: str) -> bool:
    """Return whether ``model`` accepts a non-default temperature.

    Anthropic removed sampling parameters from models released after Claude
    Opus 4.6. Canonical model IDs from the 4.6 generation onward put the
    family before the numeric version (for example, ``claude-opus-4-8``).
    Older IDs use a different shape and continue to support temperature.

    This is the *model* rule only. Ask `temperature_is_applied` for the
    question that matters at a call site or on a screen, which is whether a
    temperature will actually reach the API.
    """
    match = re.match(r"^claude-([a-z]+)-(\d+)(?:-(\d+))?(?:-|$)", model)
    if not match:
        return True

    family, major_text, minor_text = match.groups()
    version = (int(major_text), int(minor_text or 0))
    return version < (5, 0) and not (family == "opus" and version > (4, 6))


def temperature_is_applied(model: str) -> bool:
    """Whether a temperature sent for ``model`` reaches Anthropic.

    Both gates, because both can close it: the SDK has to carry the parameter
    and the model has to honour it. This is what the harness must display —
    PROJECT.md invariant 2 puts the mechanism *as sent* on the projected
    surface, so "temperature 0.3" beside a call that carried none is a false
    statement in front of a room.
    """
    return _sdk_accepts_temperature() and _supports_temperature(model)


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

    def prepare(self, messages: list[LLMMessage], params: dict | None = None, *,
                model: str | None = None) -> ProviderRequest:
        """Build a Messages request and account for every parameter.

        Three things can close the temperature gate and each is reported
        separately, because "the SDK will not carry it", "this model ignores
        it" and "extended thinking forbids it" are different facts and a
        trainer acts differently on each.
        """
        values = self.resolve_params(params)
        target_model = model or self.model
        system_text, chat = split_system(messages, values.get("system"))

        max_tokens = int(values["max_tokens"])
        payload: dict = {
            "model": target_model,
            "messages": [{"role": m.role, "content": m.content} for m in chat],
            "max_tokens": max_tokens,
        }
        sent: dict = {"max_tokens": max_tokens}
        dropped: dict[str, str] = {}

        if system_text:
            payload["system"] = system_text
            sent["system"] = system_text

        # ── deliberation budget ────────────────────────────────────────────
        think = values.get("think")
        thinking_enabled = False
        if think is not None:
            if not _sdk_accepts_thinking():
                dropped["think"] = "drop.think.sdk_lacks_parameter"
            elif think is False:
                # Absence *is* "disabled" for this API, so the request carries
                # the meaning faithfully without carrying a field.
                sent["think"] = False
            elif isinstance(think, str):
                # A level is not a budget. Rounding "high" to some number of
                # tokens would put an invented figure on a projected screen,
                # which is the one thing this layer may never do
                # (docs/specs/model-control.md §3).
                dropped["think"] = "drop.think.anthropic_takes_a_budget"
            elif think < MIN_THINKING_BUDGET:
                dropped["think"] = "drop.think.budget_below_minimum"
            elif think >= max_tokens:
                # Thinking tokens count toward max_tokens, so a budget at or
                # above the ceiling leaves nothing for an answer. Refused here
                # rather than by the API, so the reason reaches the room.
                dropped["think"] = "drop.think.budget_not_below_max_tokens"
            else:
                payload["thinking"] = {"type": "enabled", "budget_tokens": int(think)}
                sent["think"] = int(think)
                thinking_enabled = True

        # ── temperature ────────────────────────────────────────────────────
        temperature = values.get("temperature")
        if temperature is not None:
            if not _sdk_accepts_temperature():
                dropped["temperature"] = "drop.temperature.sdk_lacks_parameter"
            elif not _supports_temperature(target_model):
                dropped["temperature"] = "drop.temperature.model_ignores"
            elif thinking_enabled and float(temperature) != 1.0:
                # Extended thinking and a non-default temperature are not
                # combinable. Reported rather than quietly preferred, because
                # a pane is claiming one of the two on screen.
                dropped["temperature"] = "drop.temperature.thinking_needs_default"
            else:
                payload["temperature"] = float(temperature)
                sent["temperature"] = float(temperature)

        return ProviderRequest(model=target_model, payload=payload, sent=sent, dropped=dropped)

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
                 temperature: float | None = None, max_tokens: int | None = None,
                 params: dict | None = None,
                 request: ProviderRequest | None = None) -> LLMResponse:
        import anthropic as _anthropic
        request = request or self.prepare(
            messages, self.resolve_params(params, temperature, max_tokens), model=model
        )
        target_model = request.model
        try:
            response = self._client.messages.create(**request.payload)
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
        # `content` can hold thinking blocks before the answer when a budget was
        # sent. The text the room reads is the text blocks; the thinking blocks
        # are the model's own and are not rendered as the answer.
        content = "".join(
            block.text for block in (response.content or [])
            if getattr(block, "type", "text") == "text" and getattr(block, "text", None)
        )
        usage = ({"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
                 if response.usage else None)
        return LLMResponse(content=content, model=response.model, provider=self.provider_name, usage=usage)

    @retry_with_backoff(max_attempts=3)
    def generate_stream(self, messages: list[LLMMessage], *, model: str | None = None,
                        temperature: float | None = None, max_tokens: int | None = None,
                        params: dict | None = None,
                        request: ProviderRequest | None = None) -> Iterator[str]:
        import anthropic as _anthropic
        request = request or self.prepare(
            messages, self.resolve_params(params, temperature, max_tokens), model=model
        )
        target_model = request.model
        try:
            with self._client.messages.stream(**request.payload) as stream:
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

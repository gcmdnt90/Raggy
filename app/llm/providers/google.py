"""Google Gemini provider for Raggy.

Written against **google-genai** (`from google import genai`), which is the
package `pyproject.toml` declares and both locks pin. An earlier revision of
this file imported `google.generativeai` — the previous, separate SDK — so on
a clean checkout a configured Google key produced a pane that failed with
"Package 'google-generativeai' not installed", naming a package that is not a
dependency of this project. The verification in AGENTS.md §3 is what should
have caught it; there was no Google provider test to fail.

The two SDKs are not API-compatible: this one is client-based
(`client.models.generate_content(...)`) rather than model-object-based, takes
sampling parameters in a `GenerateContentConfig` rather than a
`GenerationConfig`, and raises `google.genai.errors.APIError` with an HTTP
status code rather than a family of per-condition exceptions.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

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
    split_system,
)
from app.llm.providers import model_catalog

logger = logging.getLogger(__name__)


def _thinking_fields(types) -> frozenset[str]:
    """Which deliberation fields the installed `ThinkingConfig` actually has.

    Google changed the shape between model generations: a `thinking_budget` in
    the 2.5 line, a `thinking_level` in the 3.x line. Rather than assume which
    one this SDK carries — and the adapter cannot know which one the *model*
    accepts either — the field is looked for and a parameter that has nowhere
    to go is dropped with a reason.
    """
    config = getattr(types, "ThinkingConfig", None)
    if config is None:
        return frozenset()
    fields = getattr(config, "model_fields", None)
    if fields:
        return frozenset(fields)
    return frozenset(getattr(config, "__annotations__", {}))


class GoogleProvider(LLMProvider):
    """Provider for Google Gemini via the google-genai SDK."""

    provider_name: str = "google"
    #: `gemini-2.5-flash` was retired under Banco between one lesson and the
    #: next — the API answered 404 with "no longer available to new users …
    #: please update your code to use models/gemini-3.6-flash". Taken from
    #: Google's own message rather than guessed. Model ids rot; pre-flight now
    #: lists what the API will actually accept when this one stops working.
    default_model: str = "gemini-3.6-flash"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if not self.api_key:
            raise LLMAuthenticationError("Google API key missing. Set GOOGLE_API_KEY in .env.")
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ImportError(
                "Package 'google-genai' not installed. It is a declared dependency; "
                "reinstall with: pip install -r requirements.lock"
            ) from exc
        self._genai = genai
        self._types = types
        self._client = genai.Client(api_key=self.api_key)

    @classmethod
    def for_inspection(cls, model: str, *, temperature: float = 0.3,
                       max_tokens: int = 1500) -> GoogleProvider:
        """As the base class, plus the `types` module `prepare` reads.

        Which deliberation field this SDK offers is exactly what pre-flight is
        asking about, so the real module is imported rather than stubbed.
        """
        provider = super().for_inspection(model, temperature=temperature,
                                          max_tokens=max_tokens)
        from google.genai import types

        provider._types = types
        return provider

    # ── Request construction ──────────────────────────────────────────────────

    def prepare(self, messages: list[LLMMessage], params: dict | None = None, *,
                model: str | None = None) -> ProviderRequest:
        """Build contents + a GenerateContentConfig, and account for the rest.

        Gemini carries the system prompt on the config rather than as a turn and
        names the assistant role "model"; everything else maps across. The
        deliberation parameter is the one that cannot be mapped blind, because
        the field that carries it changed between model generations — see
        `_thinking_fields`.
        """
        values = self.resolve_params(params)
        target_model = model or self.model
        system_text, chat = split_system(messages, values.get("system"))

        contents: list[Any] = [
            self._types.Content(
                role="model" if m.role == "assistant" else "user",
                parts=[self._types.Part.from_text(text=m.content)],
            )
            for m in chat
        ]

        temperature = float(values["temperature"])
        max_tokens = int(values["max_tokens"])
        config_kwargs: dict = {
            "system_instruction": system_text,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        sent: dict = {"temperature": temperature, "max_tokens": max_tokens}
        dropped: dict[str, str] = {}
        if system_text:
            sent["system"] = system_text

        think = values.get("think")
        if think is not None:
            fields = _thinking_fields(self._types)
            if not fields:
                dropped["think"] = "drop.think.sdk_lacks_parameter"
            elif think is False:
                # Google expresses "off" as a zero budget where budgets exist.
                # Where only levels exist there is no documented "off", so it is
                # reported as dropped rather than approximated.
                if "thinking_budget" in fields:
                    config_kwargs["thinking_config"] = self._types.ThinkingConfig(thinking_budget=0)
                    sent["think"] = False
                else:
                    dropped["think"] = "drop.think.no_off_switch"
            elif isinstance(think, str):
                if "thinking_level" in fields:
                    config_kwargs["thinking_config"] = self._types.ThinkingConfig(
                        thinking_level=think
                    )
                    sent["think"] = think
                else:
                    dropped["think"] = "drop.think.google_takes_a_budget"
            else:
                if "thinking_budget" in fields:
                    config_kwargs["thinking_config"] = self._types.ThinkingConfig(
                        thinking_budget=int(think)
                    )
                    sent["think"] = int(think)
                else:
                    dropped["think"] = "drop.think.google_takes_a_level"

        # Banco sends no tools, so automatic function calling has nothing to do
        # — but the SDK enables it by default and logs a WARNING on every
        # `generate_content` telling the caller to use `Chat.send_message`
        # instead. A warning that fires on every call and describes a feature
        # this application does not use is noise in the one log a trainer would
        # read during a failure. Set only when the installed SDK has the field.
        afc = getattr(self._types, "AutomaticFunctionCallingConfig", None)
        if afc is not None:
            config_kwargs["automatic_function_calling"] = afc(disable=True)

        config = self._types.GenerateContentConfig(**config_kwargs)
        return ProviderRequest(
            model=target_model,
            payload={"model": target_model, "contents": contents, "config": config},
            sent=sent,
            dropped=dropped,
        )

    # ── Model discovery ───────────────────────────────────────────────────────

    def _fetch_models(self) -> list[str]:
        """Query the Gemini API for models that support text generation."""
        out: list[str] = []
        for model in self._client.models.list():
            actions = getattr(model, "supported_actions", None) or []
            if "generateContent" not in actions:
                continue
            # `name` arrives as "models/gemini-2.5-flash"; the rest of Banco
            # speaks in bare model ids.
            name = (model.name or "").split("/")[-1]
            if name.startswith("gemini"):
                out.append(name)
        return out

    def available_models(self) -> list[str]:
        """Live model list from the API, with a static fallback when offline."""
        return model_catalog.discover(
            self.provider_name,
            self._fetch_models,
            cache_key=model_catalog.credential_cache_key(self.api_key),
        )

    # ── Generation ────────────────────────────────────────────────────────────

    def generate(self, messages: list[LLMMessage], *, model: str | None = None,
                 temperature: float | None = None, max_tokens: int | None = None,
                 params: dict | None = None,
                 request: ProviderRequest | None = None) -> LLMResponse:
        request = request or self.prepare(
            messages, self.resolve_params(params, temperature, max_tokens), model=model
        )
        target_model = request.model
        try:
            response = self._client.models.generate_content(**request.payload)
        except Exception as exc:
            self._handle_error(exc, target_model)

        return LLMResponse(
            content=response.text or "",
            model=target_model,
            provider=self.provider_name,
            usage=self._usage(response),
        )

    def generate_stream(self, messages: list[LLMMessage], *, model: str | None = None,
                        temperature: float | None = None,
                        max_tokens: int | None = None,
                        params: dict | None = None,
                        request: ProviderRequest | None = None) -> Iterator[str]:
        request = request or self.prepare(
            messages, self.resolve_params(params, temperature, max_tokens), model=model
        )
        target_model = request.model
        try:
            stream = self._client.models.generate_content_stream(**request.payload)
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            self._handle_error(exc, target_model)

    def test_connection(self) -> bool:
        try:
            self.generate([LLMMessage(role="user", content="ping")], max_tokens=16)
            return True
        except Exception as exc:
            # The type only. A message here would be the SDK's, and this one is
            # written to the log.
            logger.warning("Google connection test failed (%s)", type(exc).__name__)
            return False

    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        embed_model = model or "text-embedding-004"
        try:
            response = self._client.models.embed_content(model=embed_model, contents=texts)
        except Exception as exc:
            self._handle_error(exc, embed_model)
        return [list(item.values or []) for item in (response.embeddings or [])]

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _usage(response) -> dict[str, int] | None:
        meta = getattr(response, "usage_metadata", None)
        if not meta:
            return None
        return {
            "prompt_tokens": getattr(meta, "prompt_token_count", 0) or 0,
            "completion_tokens": getattr(meta, "candidates_token_count", 0) or 0,
            "total_tokens": getattr(meta, "total_token_count", 0) or 0,
        }

    def _handle_error(self, exc: Exception, model: str):
        """Map an SDK failure onto Banco's exception family.

        Classified by HTTP status where the SDK provides one, and only then by
        the message. `APIError.__str__` is `f"{code} {status}. {details}"` where
        `details` is the raw response body, so matching on the text alone is
        both fragile and a reason to be careful about where that text ends up —
        see app/utils/redact.py.
        """
        code = getattr(exc, "code", None)
        status = (getattr(exc, "status", None) or "").upper()
        text = str(exc).lower()

        if code in (401, 403) or status in {"UNAUTHENTICATED", "PERMISSION_DENIED"}:
            raise LLMAuthenticationError(str(exc)) from exc
        if code == 404 or status == "NOT_FOUND" or "not found" in text or "does not exist" in text:
            raise LLMModelNotFoundError(f"Model '{model}' not found: {exc}") from exc
        if code == 429 or status == "RESOURCE_EXHAUSTED" or "rate limit" in text:
            raise LLMRateLimitError(str(exc)) from exc
        if code == 504 or "timeout" in text or "deadline" in text:
            raise LLMTimeoutError(str(exc)) from exc
        if "api_key" in text or "api key" in text or "authenticat" in text:
            raise LLMAuthenticationError(str(exc)) from exc
        raise LLMConnectionError(str(exc)) from exc

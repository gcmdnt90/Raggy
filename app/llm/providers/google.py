"""Google Gemini provider for Raggy."""

from __future__ import annotations

import logging
from typing import Iterator

from app.llm.base import (
    LLMMessage, LLMProvider, LLMResponse,
    LLMAuthenticationError, LLMConnectionError,
    LLMModelNotFoundError, LLMTimeoutError,
)
from app.llm.providers import model_catalog

logger = logging.getLogger(__name__)


class GoogleProvider(LLMProvider):
    """Provider for Google Generative AI (Gemini)."""

    provider_name: str = "google"
    default_model: str = "gemini-2.5-flash"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if not self.api_key:
            raise LLMAuthenticationError("Google API key missing. Set GOOGLE_API_KEY in .env.")
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ImportError("Package 'google-generativeai' not installed. Run: pip install google-generativeai") from exc
        genai.configure(api_key=self.api_key)
        self._genai = genai

    def _fetch_models(self) -> list[str]:
        """Query the Gemini API for models that support text generation."""
        out: list[str] = []
        for m in self._genai.list_models():
            methods = getattr(m, "supported_generation_methods", []) or []
            if "generateContent" in methods:
                name = m.name.split("/")[-1]
                if name.startswith("gemini"):
                    out.append(name)
        return out

    def available_models(self) -> list[str]:
        """Live model list from the API, with a static fallback when offline."""
        return model_catalog.discover(self.provider_name, self._fetch_models)

    def generate(self, messages: list[LLMMessage], *, model: str | None = None,
                 temperature: float | None = None, max_tokens: int | None = None) -> LLMResponse:
        target_model = model or self.model
        system_parts, chat_history, last_user = self._convert_messages(messages)
        try:
            gen_model = self._genai.GenerativeModel(
                target_model,
                system_instruction=system_parts or None,
                generation_config=self._genai.types.GenerationConfig(
                    temperature=temperature if temperature is not None else self.temperature,
                    max_output_tokens=max_tokens or self.max_tokens,
                ),
            )
            chat = gen_model.start_chat(history=chat_history)
            response = chat.send_message(last_user)
        except Exception as exc:
            self._handle_error(exc, target_model)
        content = response.text if response.text else ""
        usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            usage = {
                "prompt_tokens": getattr(um, "prompt_token_count", 0),
                "completion_tokens": getattr(um, "candidates_token_count", 0),
                "total_tokens": getattr(um, "total_token_count", 0),
            }
        return LLMResponse(content=content, model=target_model, provider=self.provider_name, usage=usage)

    def generate_stream(self, messages: list[LLMMessage], *, model: str | None = None,
                        temperature: float | None = None, max_tokens: int | None = None) -> Iterator[str]:
        target_model = model or self.model
        system_parts, chat_history, last_user = self._convert_messages(messages)
        try:
            gen_model = self._genai.GenerativeModel(
                target_model,
                system_instruction=system_parts or None,
                generation_config=self._genai.types.GenerationConfig(
                    temperature=temperature if temperature is not None else self.temperature,
                    max_output_tokens=max_tokens or self.max_tokens,
                ),
            )
            chat = gen_model.start_chat(history=chat_history)
            response = chat.send_message(last_user, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            self._handle_error(exc, target_model)

    def test_connection(self) -> bool:
        try:
            self.generate([LLMMessage(role="user", content="ping")], max_tokens=16)
            return True
        except Exception:
            logger.exception("Google connection test failed")
            return False

    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        embed_model = model or "models/text-embedding-004"
        result = self._genai.embed_content(model=embed_model, content=texts)
        if isinstance(result["embedding"][0], list):
            return result["embedding"]
        return [result["embedding"]]

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _convert_messages(messages: list[LLMMessage]):
        system_parts = ""
        chat_history = []
        last_user = ""
        for msg in messages:
            if msg.role == "system":
                system_parts += msg.content + "\n"
            elif msg.role == "user":
                last_user = msg.content
            elif msg.role == "assistant":
                if last_user:
                    chat_history.append({"role": "user", "parts": [last_user]})
                    last_user = ""
                chat_history.append({"role": "model", "parts": [msg.content]})
        return system_parts.strip(), chat_history, last_user

    @staticmethod
    def _handle_error(exc: Exception, model: str):
        exc_str = str(exc).lower()
        if "api_key" in exc_str or "permission" in exc_str or "authenticat" in exc_str:
            raise LLMAuthenticationError(str(exc)) from exc
        if "not found" in exc_str or "does not exist" in exc_str:
            raise LLMModelNotFoundError(f"Model '{model}' not found: {exc}") from exc
        if "timeout" in exc_str or "deadline" in exc_str:
            raise LLMTimeoutError(str(exc)) from exc
        raise LLMConnectionError(str(exc)) from exc

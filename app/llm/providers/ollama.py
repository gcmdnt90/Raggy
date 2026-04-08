"""Ollama (local models) provider for Raggy."""

from __future__ import annotations

import json
import logging
from typing import Iterator

import requests

from app.llm.base import (
    LLMMessage, LLMProvider, LLMResponse,
    LLMConnectionError, LLMModelNotFoundError, LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Provider for Ollama via local REST API."""

    provider_name: str = "ollama"
    default_model: str = "gemma3:4b"

    def __init__(self, base_url: str = "http://localhost:11434", **kwargs) -> None:
        kwargs.setdefault("api_key", "")
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self.num_ctx = kwargs.get("num_ctx", 8192)
        self.keep_alive = kwargs.get("keep_alive", "30m")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    @staticmethod
    def _to_ollama_messages(messages: list[LLMMessage]) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def available_models(self) -> list[str]:
        try:
            resp = requests.get(self._url("/api/tags"), timeout=self.timeout)
            resp.raise_for_status()
        except requests.ConnectionError as exc:
            raise LLMConnectionError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
        except requests.Timeout as exc:
            raise LLMTimeoutError(str(exc)) from exc
        return [m["name"] for m in resp.json().get("models", []) if "name" in m]

    def generate(self, messages: list[LLMMessage], *, model: str | None = None,
                 temperature: float | None = None, max_tokens: int | None = None) -> LLMResponse:
        target_model = model or self.model
        payload: dict = {
            "model": target_model,
            "messages": self._to_ollama_messages(messages),
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
                "num_ctx": self.num_ctx,
                "num_gpu": -1,
            },
        }
        if max_tokens or self.max_tokens:
            payload["options"]["num_predict"] = max_tokens or self.max_tokens
        try:
            resp = requests.post(self._url("/api/chat"), json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except requests.ConnectionError as exc:
            raise LLMConnectionError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
        except requests.Timeout as exc:
            raise LLMTimeoutError(str(exc)) from exc
        except requests.HTTPError as exc:
            if resp.status_code == 404:
                raise LLMModelNotFoundError(
                    f"Model '{target_model}' not found in Ollama. Run: ollama pull {target_model}"
                ) from exc
            raise LLMConnectionError(str(exc)) from exc
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        usage: dict[str, int] | None = None
        if "prompt_eval_count" in data or "eval_count" in data:
            usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            }
        return LLMResponse(content=content, model=data.get("model", target_model),
                           provider=self.provider_name, usage=usage)

    def generate_stream(self, messages: list[LLMMessage], *, model: str | None = None,
                        temperature: float | None = None, max_tokens: int | None = None) -> Iterator[str]:
        target_model = model or self.model
        payload: dict = {
            "model": target_model,
            "messages": self._to_ollama_messages(messages),
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
                "num_ctx": self.num_ctx,
                "num_gpu": -1,
            },
        }
        if max_tokens or self.max_tokens:
            payload["options"]["num_predict"] = max_tokens or self.max_tokens
        try:
            resp = requests.post(self._url("/api/chat"), json=payload, timeout=self.timeout, stream=True)
            resp.raise_for_status()
        except requests.ConnectionError as exc:
            raise LLMConnectionError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
        except requests.Timeout as exc:
            raise LLMTimeoutError(str(exc)) from exc
        except requests.HTTPError as exc:
            if resp.status_code == 404:
                raise LLMModelNotFoundError(f"Model '{target_model}' not found in Ollama.") from exc
            raise LLMConnectionError(str(exc)) from exc
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content
            if chunk.get("done", False):
                break

    def test_connection(self) -> bool:
        try:
            resp = requests.get(self._url("/api/tags"), timeout=10)
            return resp.status_code == 200
        except Exception:
            logger.exception("Ollama connection test failed")
            return False

    def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        embed_model = model or self.model
        # Try batch endpoint /api/embed (Ollama 0.4.0+)
        try:
            resp = requests.post(
                self._url("/api/embed"),
                json={"model": embed_model, "input": texts, "keep_alive": self.keep_alive},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if "embeddings" in data:
                return data["embeddings"]
        except requests.HTTPError as exc:
            if resp.status_code == 404:
                logger.debug("Batch /api/embed not available, falling back to /api/embeddings.")
            else:
                raise LLMConnectionError(str(exc)) from exc
        except requests.ConnectionError as exc:
            raise LLMConnectionError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
        except requests.Timeout as exc:
            raise LLMTimeoutError(str(exc)) from exc
        # Sequential fallback
        embeddings: list[list[float]] = []
        for text in texts:
            try:
                resp = requests.post(
                    self._url("/api/embeddings"),
                    json={"model": embed_model, "prompt": text},
                    timeout=self.timeout,
                )
                resp.raise_for_status()
            except requests.ConnectionError as exc:
                raise LLMConnectionError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
            except requests.Timeout as exc:
                raise LLMTimeoutError(str(exc)) from exc
            except requests.HTTPError as exc:
                if resp.status_code == 404:
                    raise LLMModelNotFoundError(f"Model '{embed_model}' not found in Ollama.") from exc
                raise LLMConnectionError(str(exc)) from exc
            embeddings.append(resp.json().get("embedding", []))
        return embeddings

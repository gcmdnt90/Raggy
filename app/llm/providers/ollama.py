"""Ollama (local models) provider for Raggy."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import requests

from app.llm.base import (
    LLMConnectionError,
    LLMMessage,
    LLMModelNotFoundError,
    LLMProvider,
    LLMResponse,
    LLMTimeoutError,
    ProviderRequest,
    split_system,
)

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Provider for Ollama via local REST API."""

    provider_name: str = "ollama"
    default_model: str = "gemma3:4b"
    #: What `for_inspection` must set for `prepare` to run without a client.
    INSPECTION_DEFAULTS = {"num_ctx": 8192, "keep_alive": "30m",
                           "base_url": "http://localhost:11434"}

    def __init__(self, base_url: str = "http://localhost:11434", **kwargs) -> None:
        kwargs.setdefault("api_key", "")
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self.num_ctx = kwargs.get("num_ctx", 8192)
        self.keep_alive = kwargs.get("keep_alive", "30m")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def prepare(self, messages: list[LLMMessage], params: dict | None = None, *,
                model: str | None = None) -> ProviderRequest:
        """Build an `/api/chat` body.

        Ollama is the one source that speaks both shapes of deliberation:
        `think` takes `true`/`false` or a level. It does not take a token
        budget, so an integer budget is dropped with its reason rather than
        approximated — an approximated budget beside a claim that deliberation
        *is* a budget would be a false statement on a projected screen.
        """
        values = self.resolve_params(params)
        target_model = model or self.model
        system_text, chat = split_system(messages, values.get("system"))

        conversation = ([{"role": "system", "content": system_text}] if system_text else [])
        conversation += [{"role": m.role, "content": m.content} for m in chat]

        temperature = float(values["temperature"])
        max_tokens = int(values["max_tokens"])
        payload: dict = {
            "model": target_model,
            "messages": conversation,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
                "num_ctx": self.num_ctx,
                "num_gpu": -1,
                "num_predict": max_tokens,
            },
        }
        sent: dict = {"temperature": temperature, "max_tokens": max_tokens}
        dropped: dict[str, str] = {}
        if system_text:
            sent["system"] = system_text

        think = values.get("think")
        if think is not None:
            if isinstance(think, bool) or isinstance(think, str):
                # A level or a boolean goes through untouched. Some models take
                # only one of the two and reject the other; that refusal is the
                # model's and is narrated as a pane failure, not guessed at here.
                payload["think"] = think
                sent["think"] = think
            else:
                dropped["think"] = "drop.think.ollama_takes_boolean_or_level"

        return ProviderRequest(model=target_model, payload=payload, sent=sent, dropped=dropped)

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
                 temperature: float | None = None, max_tokens: int | None = None,
                 params: dict | None = None,
                 request: ProviderRequest | None = None) -> LLMResponse:
        request = request or self.prepare(
            messages, self.resolve_params(params, temperature, max_tokens), model=model
        )
        target_model = request.model
        payload = {**request.payload, "stream": False}
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
                        temperature: float | None = None, max_tokens: int | None = None,
                        params: dict | None = None,
                        request: ProviderRequest | None = None) -> Iterator[str]:
        request = request or self.prepare(
            messages, self.resolve_params(params, temperature, max_tokens), model=model
        )
        target_model = request.model
        payload = {**request.payload, "stream": True}
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

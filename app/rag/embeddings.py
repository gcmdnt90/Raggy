"""Embedding management for Raggy."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _configure_hf_token(token: str | None = None) -> None:
    """Set the Hugging Face token for authenticated requests.

    Priority:
    1. Explicit *token* argument (from Settings / .env HF_TOKEN)
    2. Already set HF_TOKEN / HUGGINGFACE_HUB_TOKEN env vars (no-op)

    Benefits: higher rate limits, faster downloads, access to gated models.
    """
    if token:
        os.environ.setdefault("HF_TOKEN", token)
        try:
            from huggingface_hub import login
            login(token=token, add_to_git_credential=False)
            logger.debug("Hugging Face authenticated with HF_TOKEN.")
        except Exception as exc:
            logger.warning("HF login failed (token ignored): %s", exc)
    elif not os.environ.get("HF_TOKEN") and not os.environ.get("HUGGINGFACE_HUB_TOKEN"):
        logger.debug(
            "HF_TOKEN not configured — public downloads with lower rate limits. "
            "Set HF_TOKEN in .env to avoid limitations."
        )


class EmbeddingManager:
    """Manages embeddings independently of the LLM provider."""

    def __init__(self, provider: str = "local", model: str | None = None, **kwargs):
        self.provider = provider
        self._model = None

        # Authenticate with HF Hub if a token is provided or in env
        hf_token = kwargs.get("hf_token") or os.environ.get("HF_TOKEN") or ""
        _configure_hf_token(hf_token or None)

        if provider == "local":
            self.model_name = model or "paraphrase-multilingual-MiniLM-L12-v2"
            self._embed_fn = self._embed_local
        elif provider == "openai":
            self._api_key = kwargs.get("api_key", "")
            self.model_name = model or "text-embedding-3-small"
            self._embed_fn = self._embed_openai
        elif provider == "ollama":
            self._base_url = kwargs.get("base_url", "http://localhost:11434")
            self.model_name = model or "nomic-embed-text"
            self._embed_fn = self._embed_ollama
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")

    def _get_local_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def preload(self) -> None:
        """Pre-load the embedding model (avoids latency on first query)."""
        if self.provider == "local":
            self._get_local_model()
            logger.info("Local embedding model pre-loaded: %s", self.model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for the given texts."""
        return self._embed_fn(texts)

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        model = self._get_local_model()
        return model.encode(texts).tolist()

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI
        client = OpenAI(api_key=self._api_key)
        response = client.embeddings.create(model=self.model_name, input=texts)
        return [item.embedding for item in response.data]

    def _embed_ollama(self, texts: list[str]) -> list[list[float]]:
        import requests
        # Try batch endpoint /api/embed (Ollama 0.4.0+)
        try:
            resp = requests.post(
                f"{self._base_url}/api/embed",
                json={"model": self.model_name, "input": texts},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            if "embeddings" in data:
                return data["embeddings"]
        except requests.HTTPError:
            logger.debug("Batch /api/embed not available, falling back to /api/embeddings.")
        # Sequential fallback
        embeddings = []
        for text in texts:
            resp = requests.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
                timeout=60,
            )
            resp.raise_for_status()
            embeddings.append(resp.json()["embedding"])
        return embeddings

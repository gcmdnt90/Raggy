"""Retriever for querying the Knowledge Base in ChromaDB."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.config import CHROMA_PERSIST_DIR
from app.rag.embeddings import EmbeddingManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton ChromaDB client cache — avoids race conditions when creating
# multiple PersistentClient instances to the same path.
# ---------------------------------------------------------------------------
_chroma_client_cache: dict[str, Any] = {}


def get_chroma_client(path: str | None = None):
    """Return a shared PersistentClient for *path* (creates it on first call)."""
    import chromadb

    resolved = path or str(CHROMA_PERSIST_DIR)
    if resolved not in _chroma_client_cache:
        logger.debug("Creating ChromaDB PersistentClient: %s", resolved)
        try:
            _chroma_client_cache[resolved] = chromadb.PersistentClient(path=resolved)
        except (AttributeError, ValueError):
            _clear_chroma_system_cache()
            _chroma_client_cache[resolved] = chromadb.PersistentClient(path=resolved)
    return _chroma_client_cache[resolved]


def close_chroma_clients():
    """Close all cached ChromaDB clients, releasing file locks (e.g. SQLite)."""
    for path, client in list(_chroma_client_cache.items()):
        try:
            if hasattr(client, "close"):
                client.close()
            elif hasattr(client, "_server") and hasattr(client._server, "stop"):
                client._server.stop()
        except Exception:
            logger.debug("Failed to close ChromaDB client for %s", path, exc_info=True)
    _chroma_client_cache.clear()
    _clear_chroma_system_cache()
    logger.debug("All cached ChromaDB clients closed.")


def _clear_chroma_system_cache() -> None:
    """Clear Chroma's process-wide shared system cache after closing clients."""
    try:
        from chromadb.api.shared_system_client import SharedSystemClient

        SharedSystemClient.clear_system_cache()
    except Exception:
        logger.debug("Failed to clear ChromaDB shared system cache", exc_info=True)


@dataclass
class RetrievedChunk:
    text: str
    metadata: dict
    score: float


class ChromaRetriever:
    """Retrieve relevant chunks from the Knowledge Base via ChromaDB."""

    def __init__(
        self,
        persist_dir: str | None = None,
        embedding_manager: EmbeddingManager | None = None,
    ):
        from app.config import get_settings
        path = persist_dir or str(CHROMA_PERSIST_DIR)
        self.client = get_chroma_client(path)
        self.collection = self.client.get_collection("raggy_kb")
        if embedding_manager is None:
            settings = get_settings()
            embedding_manager = EmbeddingManager(hf_token=settings.hf_token)
        self.embedding_manager = embedding_manager

    def retrieve(
        self,
        query: str,
        k: int = 5,
        category: str | None = None,
    ) -> list[RetrievedChunk]:
        """Retrieve the most relevant chunks from the KB."""
        where_filter = None
        if category:
            where_filter = {"category": category}

        query_embedding = self.embedding_manager.embed([query])[0]

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        return [
            RetrievedChunk(
                text=doc,
                metadata=meta,
                score=max(0, 1 - dist),
            )
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

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
        _chroma_client_cache[resolved] = chromadb.PersistentClient(path=resolved)
    return _chroma_client_cache[resolved]


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

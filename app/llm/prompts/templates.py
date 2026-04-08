"""Template rendering utilities for Raggy prompts.

Provides helper functions to format RAG context for insertion into LLM prompts.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def render_rag_context(context: dict[str, Any]) -> str:
    """Format RAG-retrieved chunks for inclusion in an LLM prompt.

    Supports multiple context formats:
    - ``{"chunks": [{"text": ..., "source": ..., "score": ...}, ...]}``
    - ``{"documents": ["text1", "text2", ...]}``
    - ``{"text": "single text"}``

    Returns:
        Formatted string with numbered chunks, or empty string if no content.
    """
    if not context:
        return ""

    sections: list[str] = []

    # Format 1: structured chunks
    chunks = context.get("chunks", [])
    if chunks:
        for i, chunk in enumerate(chunks, 1):
            text = chunk.get("text", "").strip()
            if not text:
                continue
            source = chunk.get("source", "unknown")
            score = chunk.get("score")
            header = f"### Source {i}: {source}"
            if score is not None:
                header += f" (relevance: {score:.2f})"
            sections.append(f"{header}\n{text}")
        if sections:
            return "\n\n".join(sections)

    # Format 2: list of document strings
    documents = context.get("documents", [])
    if documents:
        for i, doc in enumerate(documents, 1):
            doc_text = doc.strip() if isinstance(doc, str) else str(doc).strip()
            if doc_text:
                sections.append(f"### Document {i}\n{doc_text}")
        if sections:
            return "\n\n".join(sections)

    # Format 3: single text
    text = context.get("text", "").strip()
    if text:
        return text

    return ""

"""Plain text and Markdown loaders."""

from __future__ import annotations

from pathlib import Path

from app.parsers.documents import ParsedDocument
from app.utils.sanitize import read_binary, validate_text_bytes


def load_text(path: str | Path) -> ParsedDocument:
    """Load and validate a UTF-8 text or Markdown document."""
    p = Path(path)
    data = read_binary(p)
    text = validate_text_bytes(data)
    return ParsedDocument(
        text=text,
        metadata={
            "source_file": str(p),
            "format": p.suffix.lower().lstrip("."),
            "size_bytes": len(data),
        },
    )

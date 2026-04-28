"""PDF document loader."""

from __future__ import annotations

import io
from pathlib import Path

from app.parsers.documents import ParsedDocument
from app.utils.sanitize import sanitize_text, validate_pdf


def load_pdf(path: str | Path) -> ParsedDocument:
    """Load and validate a PDF document."""
    import pdfplumber

    p = Path(path)
    validated = validate_pdf(p)
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(validated.data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(sanitize_text(page_text))

    return ParsedDocument(
        text="\n\n".join(text_parts),
        metadata={
            "source_file": str(p),
            "format": "pdf",
            "page_count": validated.page_count,
            "size_bytes": validated.size_bytes,
            "has_javascript": validated.has_javascript,
        },
    )

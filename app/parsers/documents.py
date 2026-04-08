"""Generic document parser for Raggy — handles PDF, MD, and TXT files."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text(filepath: str | Path) -> str:
    """Extract plain text from a file.

    Supports:
    - .md  — read as-is
    - .txt — read as-is
    - .pdf — extract via pdfplumber (if installed)

    Returns:
        The extracted text content.

    Raises:
        ValueError: if the file type is not supported.
        FileNotFoundError: if the file does not exist.
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()

    if suffix in (".md", ".txt"):
        return path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        return _extract_pdf(path)

    raise ValueError(
        f"Unsupported file type: {suffix}. Supported: .md, .txt, .pdf"
    )


def _extract_pdf(path: Path) -> str:
    """Extract text from a PDF using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber is required for PDF parsing. Install with: pip install pdfplumber"
        )

    text_parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n\n".join(text_parts)


def list_supported_files(directory: str | Path) -> list[Path]:
    """List all supported document files in a directory (recursive).

    Returns:
        Sorted list of Path objects for .md, .txt, .pdf files.
    """
    d = Path(directory)
    if not d.is_dir():
        return []

    extensions = {".md", ".txt", ".pdf"}
    files = [
        f for f in d.rglob("*")
        if f.is_file() and f.suffix.lower() in extensions
    ]
    return sorted(files)

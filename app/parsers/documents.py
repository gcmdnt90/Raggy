"""Generic document parser for Raggy."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".xlsx"}
REJECTED_EXTENSIONS = {".docm", ".xlsm", ".xlsb"}


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Format-agnostic parsed document."""

    text: str
    metadata: dict


def load_document(filepath: str | Path) -> ParsedDocument:
    """Load a supported document and return text plus metadata."""
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix in REJECTED_EXTENSIONS:
        raise ValueError(f"Unsupported unsafe file type: {suffix}")

    if suffix in (".md", ".txt"):
        from app.parsers.text import load_text

        return load_text(path)

    if suffix == ".pdf":
        from app.parsers.pdf import load_pdf

        return load_pdf(path)

    if suffix == ".docx":
        from app.parsers.docx import load_docx

        return load_docx(path)

    if suffix == ".xlsx":
        from app.parsers.xlsx import load_xlsx

        return load_xlsx(path)

    raise ValueError(
        f"Unsupported file type: {suffix}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )


def extract_text(filepath: str | Path) -> str:
    """Extract plain text from a supported file."""
    return load_document(filepath).text


def list_supported_files(directory: str | Path) -> list[Path]:
    """List all supported document files in a directory recursively."""
    d = Path(directory)
    if not d.is_dir():
        return []

    files = [
        f for f in d.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files)

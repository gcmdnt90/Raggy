"""Input sanitization and document validation helpers."""

from __future__ import annotations

import io
import unicodedata
import zipfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

PDF_MAX_SIZE_BYTES = 5 * 1024 * 1024
PDF_MAX_PAGES = 20
PDF_PARSE_TIMEOUT_SECONDS = 10

TEXT_MAX_SIZE_BYTES = 1 * 1024 * 1024
OOXML_MAX_SIZE_BYTES = 10 * 1024 * 1024
# A ZIP container declares how large its members expand to, so a 10 MB upload
# can claim to unpack to petabytes. Cap the declared total as well as the
# compressed size, or the size check above is decorative.
OOXML_MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
XLSX_MAX_CELLS = 100_000

_ZERO_WIDTH_CHARS = {
    "\u200b",
    "\u200c",
    "\u200d",
    "\u200e",
    "\u200f",
    "\u2060",
    "\ufeff",
}


@dataclass(frozen=True, slots=True)
class ValidatedPDF:
    """Validated PDF payload."""

    data: bytes
    page_count: int
    size_bytes: int
    has_javascript: bool = False


@dataclass(frozen=True, slots=True)
class ValidatedOOXML:
    """Validated Office Open XML payload."""

    data: bytes
    size_bytes: int


def normalize_unicode(text: str | None) -> str:
    """Normalize text with Unicode NFKC."""
    return unicodedata.normalize("NFKC", text or "")


def strip_control_chars(text: str | None) -> str:
    """Remove control and zero-width characters while preserving whitespace."""
    cleaned: list[str] = []
    for char in text or "":
        if char in _ZERO_WIDTH_CHARS:
            continue
        if unicodedata.category(char) == "Cc" and char not in "\n\r\t":
            continue
        cleaned.append(char)
    return "".join(cleaned)


def sanitize_text(text: str | None) -> str:
    """Normalize and strip unsafe invisible/control characters."""
    return strip_control_chars(normalize_unicode(text))


def read_binary(file_or_path: str | Path | bytes | BinaryIO) -> bytes:
    """Read bytes from a path, bytes object, or file-like object."""
    if isinstance(file_or_path, bytes):
        return file_or_path
    if isinstance(file_or_path, (str, Path)):
        return Path(file_or_path).read_bytes()

    pos = None
    if hasattr(file_or_path, "tell") and hasattr(file_or_path, "seek"):
        try:
            pos = file_or_path.tell()
            file_or_path.seek(0)
        except Exception:
            pos = None
    data = file_or_path.read()
    if pos is not None:
        try:
            file_or_path.seek(pos)
        except Exception:
            pass
    return data if isinstance(data, bytes) else bytes(data)


def _count_pdf_pages(data: bytes) -> int:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return len(pdf.pages)


def validate_pdf(file_or_path: str | Path | bytes | BinaryIO) -> ValidatedPDF:
    """Validate PDF magic bytes, size, page count, and parse time."""
    data = read_binary(file_or_path)
    size = len(data)
    if not data.startswith(b"%PDF-"):
        raise ValueError("Invalid PDF: missing PDF magic bytes.")
    if size > PDF_MAX_SIZE_BYTES:
        raise ValueError(f"PDF too large: {size} bytes exceeds {PDF_MAX_SIZE_BYTES}.")
    if b"/JavaScript" in data or b"/JS" in data:
        raise ValueError("PDF contains embedded JavaScript and is not accepted.")

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_count_pdf_pages, data)
    try:
        page_count = future.result(timeout=PDF_PARSE_TIMEOUT_SECONDS)
    except FuturesTimeoutError as exc:
        future.cancel()
        raise ValueError("PDF validation timed out.") from exc
    except Exception as exc:
        raise ValueError(f"PDF could not be parsed: {exc}") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    if page_count > PDF_MAX_PAGES:
        raise ValueError(f"PDF has too many pages: {page_count} exceeds {PDF_MAX_PAGES}.")
    return ValidatedPDF(data=data, page_count=page_count, size_bytes=size)


def validate_text_bytes(data: bytes, *, max_size: int = TEXT_MAX_SIZE_BYTES) -> str:
    """Validate and decode UTF-8 text bytes."""
    if len(data) > max_size:
        raise ValueError(f"Text file too large: {len(data)} bytes exceeds {max_size}.")
    try:
        return sanitize_text(data.decode("utf-8", errors="strict"))
    except UnicodeDecodeError as exc:
        raise ValueError("Text file must be valid UTF-8.") from exc


def _is_unsafe_member_path(name: str) -> bool:
    """True if a ZIP member name could escape the directory it unpacks into.

    An Office Open XML part name is a plain relative POSIX path. Anything that
    is absolute, climbs with "..", or carries a Windows separator or drive
    letter is either malformed or an attempt at path traversal, and Banco is
    delivered on Windows where "..\\" and "C:" both matter.
    """
    if not name:
        return True
    if "\\" in name or ":" in name:
        return True
    if name.startswith("/"):
        return True
    return any(part == ".." for part in PurePosixPath(name).parts)


def _assert_safe_members(archive: zipfile.ZipFile, *, kind: str) -> None:
    """Reject traversal paths and declared-size bombs before anything is read.

    The sizes checked here are the ones the container declares in its own
    headers, which a hostile archive can understate. That is still worth
    checking - it stops the ordinary decompression bomb, which works precisely
    by declaring its true, enormous size - but it is not a substitute for
    bounding what a parser actually reads.
    """
    total_uncompressed = 0
    for info in archive.infolist():
        if _is_unsafe_member_path(info.filename):
            raise ValueError(f"Invalid {kind}: unsafe member path {info.filename!r}.")
        total_uncompressed += info.file_size
        if total_uncompressed > OOXML_MAX_UNCOMPRESSED_BYTES:
            raise ValueError(
                f"{kind} too large: {total_uncompressed} bytes uncompressed exceeds "
                f"{OOXML_MAX_UNCOMPRESSED_BYTES}."
            )


def _validate_zip_payload(data: bytes, *, kind: str) -> zipfile.ZipFile:
    if not data.startswith(b"PK\x03\x04"):
        raise ValueError(f"Invalid {kind}: missing ZIP magic bytes.")
    if len(data) > OOXML_MAX_SIZE_BYTES:
        raise ValueError(f"{kind} too large: {len(data)} bytes exceeds {OOXML_MAX_SIZE_BYTES}.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid {kind}: corrupt ZIP container.") from exc

    try:
        _assert_safe_members(archive, kind=kind)
    except Exception:
        archive.close()
        raise
    return archive


def validate_docx(file_or_path: str | Path | bytes | BinaryIO) -> ValidatedOOXML:
    """Validate a macro-free DOCX Office Open XML payload."""
    data = read_binary(file_or_path)
    with _validate_zip_payload(data, kind="DOCX") as archive:
        names = set(archive.namelist())
        if "[Content_Types].xml" not in names or "word/document.xml" not in names:
            raise ValueError("Invalid DOCX: missing Office Open XML document parts.")
        content_types = archive.read("[Content_Types].xml")
        if b"wordprocessingml.document" not in content_types:
            raise ValueError("Invalid DOCX: missing WordprocessingML content type.")
        if any(name.startswith("word/vbaProject") for name in names):
            raise ValueError("Macro-enabled Word documents are not supported.")
    return ValidatedOOXML(data=data, size_bytes=len(data))


def validate_xlsx(file_or_path: str | Path | bytes | BinaryIO) -> ValidatedOOXML:
    """Validate a macro-free XLSX Office Open XML payload."""
    data = read_binary(file_or_path)
    with _validate_zip_payload(data, kind="XLSX") as archive:
        names = set(archive.namelist())
        if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
            raise ValueError("Invalid XLSX: missing Office Open XML workbook parts.")
        content_types = archive.read("[Content_Types].xml")
        if b"spreadsheetml.sheet" not in content_types:
            raise ValueError("Invalid XLSX: missing SpreadsheetML content type.")
        if any(name.startswith("xl/vbaProject") for name in names):
            raise ValueError("Macro-enabled Excel workbooks are not supported.")
    return ValidatedOOXML(data=data, size_bytes=len(data))

"""Tests for sanitization and validation helpers."""

import io
import zipfile

import pytest

from app.utils import sanitize


def test_sanitize_text_normalizes_and_strips_control_chars():
    text = "ＡＢＣ\u200b\x00\nok"
    assert sanitize.sanitize_text(text) == "ABC\nok"


def test_sanitize_text_treats_none_as_empty():
    assert sanitize.sanitize_text(None) == ""


def test_validate_text_bytes_rejects_invalid_utf8():
    with pytest.raises(ValueError, match="UTF-8"):
        sanitize.validate_text_bytes(b"\xff\xfe")


def test_validate_pdf_requires_magic_bytes():
    with pytest.raises(ValueError, match="magic"):
        sanitize.validate_pdf(b"not a pdf")


def test_validate_pdf_rejects_embedded_javascript():
    with pytest.raises(ValueError, match="JavaScript"):
        sanitize.validate_pdf(b"%PDF-1.7\n/JavaScript")


def test_validate_pdf_accepts_small_pdf(monkeypatch):
    monkeypatch.setattr(sanitize, "_count_pdf_pages", lambda data: 2)
    validated = sanitize.validate_pdf(b"%PDF-1.7\nbody")
    assert validated.page_count == 2
    assert validated.size_bytes == len(b"%PDF-1.7\nbody")


def test_validate_docx_rejects_bad_magic():
    with pytest.raises(ValueError, match="magic"):
        sanitize.validate_docx(b"not docx")


def test_validate_xlsx_rejects_bad_magic():
    with pytest.raises(ValueError, match="magic"):
        sanitize.validate_xlsx(b"not xlsx")


def _docx_with_member(name: str, payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types><Override ContentType="application/vnd.openxmlformats-'
            'officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        archive.writestr("word/document.xml", "<w:document/>")
        archive.writestr(name, payload)
    return buffer.getvalue()


def test_validate_docx_rejects_excessive_uncompressed_size(monkeypatch):
    monkeypatch.setattr(sanitize, "OOXML_MAX_UNCOMPRESSED_BYTES", 128, raising=False)
    data = _docx_with_member("word/media/bomb.bin", b"A" * 1024)

    with pytest.raises(ValueError, match="uncompressed"):
        sanitize.validate_docx(data)


def test_validate_docx_rejects_unsafe_member_path():
    data = _docx_with_member("../outside.bin", b"payload")

    with pytest.raises(ValueError, match="unsafe member path"):
        sanitize.validate_docx(data)

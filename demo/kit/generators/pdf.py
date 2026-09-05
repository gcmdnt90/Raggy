"""Minimal PDF rendering helpers built on reportlab.

Kept deliberately small: these documents exist to be *read by an agent*, not to
win a design award. Plain text extraction must be clean, so no tables, no
multi-column layouts, no images.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

FOOTER = "Documento sintetico generato per formazione — non usare in produzione."

_base = getSampleStyleSheet()

STYLES = {
    "title": ParagraphStyle(
        "t", parent=_base["Title"], fontName="Helvetica-Bold",
        fontSize=17, leading=21, spaceAfter=4, alignment=0,
        textColor=HexColor("#243044"),
    ),
    "subtitle": ParagraphStyle(
        "s", parent=_base["Normal"], fontName="Helvetica",
        fontSize=10, leading=13, spaceAfter=12, textColor=HexColor("#6b7788"),
    ),
    "h2": ParagraphStyle(
        "h2", parent=_base["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, spaceBefore=10, spaceAfter=4,
        textColor=HexColor("#243044"),
    ),
    "body": ParagraphStyle(
        "b", parent=_base["Normal"], fontName="Helvetica",
        fontSize=10.5, leading=15, spaceAfter=5,
    ),
    "field": ParagraphStyle(
        "f", parent=_base["Normal"], fontName="Helvetica",
        fontSize=10.5, leading=16, spaceAfter=1, leftIndent=6,
    ),
    # Small, low-contrast: readable by a text extractor, easy to miss on screen.
    # This is the whole point of the indirect-injection demo.
    "hidden": ParagraphStyle(
        "hid", parent=_base["Normal"], fontName="Helvetica",
        fontSize=4.6, leading=5.4, textColor=Color(0.88, 0.88, 0.88),
    ),
}


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(HexColor("#9aa5b1"))
    canvas.drawString(20 * mm, 12 * mm, FOOTER)
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"p. {doc.page}")
    canvas.restoreState()


def write_pdf(path: Path, blocks: list[tuple[str, str]]) -> Path:
    """Render (style_name, text) blocks to a single PDF.

    A block of ("spacer", "6") inserts vertical space.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title=path.stem, author="AI Translator — synthetic demo data",
    )
    flow = []
    for style, text in blocks:
        if style == "spacer":
            flow.append(Spacer(1, float(text)))
        else:
            flow.append(Paragraph(text, STYLES[style]))
    doc.build(flow, onFirstPage=_footer, onLaterPages=_footer)
    return path

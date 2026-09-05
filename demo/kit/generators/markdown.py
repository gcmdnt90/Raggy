"""Markdown rendering of the same block list the PDF builders use.

Module 3 runs the *same* documents on two rungs — a Claude Project and Raggy —
and the comparison is only readable if both read identical bytes. Raggy embeds
Markdown, so Markdown is the source of truth for the house documents and the
PDF is the printable mirror of it.
"""
from __future__ import annotations

import re
from pathlib import Path

FOOTER = "Documento sintetico generato per formazione — non usare in produzione."


def _inline(text: str) -> str:
    """reportlab inline markup and HTML escapes → Markdown."""
    text = re.sub(r"</?b>", "**", text)
    text = re.sub(r"</?i>", "*", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return text.strip()


def write_md(path: Path, blocks: list[tuple[str, str]]) -> Path:
    """Render (kind, text) blocks as Markdown. Kinds match STYLES in pdf.py."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for kind, text in blocks:
        if kind == "spacer":
            lines.append("")
            continue
        body = _inline(text)
        if kind == "title":
            lines += [f"# {body}", ""]
        elif kind == "subtitle":
            lines += [f"*{body}*", ""]
        elif kind == "h2":
            lines += ["", f"## {body}", ""]
        elif kind == "field":
            if body.startswith("•"):
                lines.append(body.replace("•", "-", 1))
            elif re.match(r"^\d+\.\s", body):      # "1. field" → ordered list
                lines.append(body)
            else:                                   # "3.1 rule", "**Label**: text"
                lines.append(f"- {body}")
        else:  # body, and anything unknown
            lines += [body, ""]
    lines += ["", "---", "", f"_{FOOTER}_", ""]
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    path.write_text(out, encoding="utf-8")
    return path

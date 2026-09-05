# -*- coding: utf-8 -*-
"""Shared spine: everything that does not depend on the sector.

A sector module (generators/settori/<sector>.py) owns its record shape, its
house documents and its sheet layout. Everything else — escaping, the ground
truth key, the demo snippets file writer, the README — lives here and is
written once.

The contract a sector module must satisfy is documented in
generators/settori/__init__.py.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


def esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_ground_truth(records: list, cols: list[str], out_dir: Path,
                       name: str = "ground-truth.csv") -> Path:
    """The trainer's answer key for the M4 verification step.

    Keep this OUT of the folder the agent is pointed at, or the demo is
    pointless — it would simply read the answers.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for rec in records:
            w.writerow(rec.as_dict())
    return path


def write_demo_files(files: dict[str, str], out_dir: Path) -> list[Path]:
    """Write the paste-ready snippets the earlier demos need.

    These exist so that M1, M2 and M4 talk about the *same* sale, the same
    month, the same commissioning run as M3 and M5 — one body of synthetic
    facts, not five unrelated ones.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in files.items():
        path = out_dir / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def as_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def five_attributes_md(title: str, pairs: list[tuple[str, str]], hint: str) -> str:
    """m2-p1: five attributes of one real record, ready to paste."""
    lines = [f"# {title}", "", hint, ""]
    lines += [f"- {k}: {v}" for k, v in pairs]
    lines += ["", "_Dati sintetici generati per formazione._", ""]
    return "\n".join(lines)


def three_candidates_md(title: str, hint: str, criteria: list[str],
                        rows: list[dict]) -> str:
    """m2-p2: three candidates scored on the three criteria the prompt names."""
    lines = [f"# {title}", "", hint, "",
             "| " + " | ".join(["Candidato"] + criteria) + " |",
             "|" + "|".join(["---"] * (len(criteria) + 1)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join([r["label"]] + [str(r[c]) for c in criteria]) + " |")
    lines += ["", "_Dati sintetici generati per formazione._", ""]
    return "\n".join(lines)


def standard_house_docs(config: dict, out_dir: Path, texts: dict,
                        stem: str, guide_stem: str) -> list[Path]:
    """The two house documents, in the shape every sector uses.

    Section 1 is the invented internal scale, section 2 the mandatory fields,
    section 3 the drafting rules, section 4 responsibility. `texts` supplies
    the sector's wording for the titles and the two prose paragraphs.
    """
    from .markdown import write_md
    from .pdf import write_pdf

    c = config
    blocks: list[tuple[str, str]] = [
        ("title", f"{esc(c['display_name'])} — {texts['rules_title']}"),
        ("subtitle", texts["rules_subtitle"]),
        ("h2", f"1. {texts['scale_section']}"),
        ("body", texts["scale_intro"]),
    ]
    for g in c["grades"]:
        blocks.append(("field", f"<b>{esc(g['code'])} — {esc(g['label'])}</b>: {esc(g['definition'])}"))
    blocks += [("h2", f"2. {texts['fields_section']}"),
               ("body", texts["fields_intro"])]
    for i, f in enumerate(c["mandatory_fields"], 1):
        blocks.append(("field", f"{i}. {esc(f)}"))
    blocks += [("h2", "3. Regole di redazione")]
    for i, r in enumerate(c["house_rules"], 1):
        blocks.append(("field", f"3.{i} {esc(r)}"))
    blocks += [("h2", "4. Responsabilità"), ("body", texts["responsibility"])]

    write_md(out_dir / f"{stem}.md", blocks)
    rules_pdf = write_pdf(out_dir / f"{stem}.pdf", blocks)

    guide: list[tuple[str, str]] = [
        ("title", texts["guide_title"]),
        ("subtitle", "Promemoria operativo per lo staff. Estratto del regolamento, sezione 1."),
        ("body", texts["guide_intro"]),
    ]
    for g in c["grades"]:
        guide += [("h2", f"{esc(g['code'])} — {esc(g['label'])}"), ("body", esc(g["definition"]))]
    guide += [("h2", "Errori frequenti")]
    for e in texts["common_errors"]:
        guide.append(("field", f"• {esc(e)}"))
    write_md(out_dir / f"{guide_stem}.md", guide)
    guide_pdf = write_pdf(out_dir / f"{guide_stem}.pdf", guide)
    return [rules_pdf, guide_pdf]


def pick_tradeoff(items: list, keys: list, profile) -> list:
    """Pick one item per criterion, so the candidates actually disagree.

    M2 asks the room to argue for one of three. Three candidates where the same
    one wins on every criterion turn that into a formality: the demo needs a
    real trade-off. One `key` per criterion, each picking its own champion, and
    `profile` decides when two items are indistinguishable.
    """
    if len(items) <= len(keys):
        return list(items)

    def dominated(cand, others) -> bool:
        """True if some already-picked item beats `cand` on every criterion.

        Every key is written so that higher is better. A candidate that loses
        on all of them is not a candidate: it is a distractor, and the room
        picks it apart instead of arguing the trade-off.
        """
        return any(all(key(o) >= key(cand) for key in keys)
                   and any(key(o) > key(cand) for key in keys)
                   for o in others)

    picked: list = []
    for key in keys:
        taken = {profile(i) for i in picked}
        ranked = sorted(items, key=key, reverse=True)
        chosen = next((i for i in ranked
                       if profile(i) not in taken and not dominated(i, picked)), None)
        if chosen is None:  # nothing undominated left: fall back to distinctness
            chosen = next((i for i in ranked if profile(i) not in taken), None)
        if chosen is None:
            chosen = next((i for i in ranked if i not in picked), None)
        if chosen is not None:
            picked.append(chosen)
    return picked[:len(keys)]

"""Numismatics document builders: house rules, grading guide, lot sheets.

The house documents are the *only* place where the grading scale and the
mandatory-field list exist. That is what makes the Module 3 grounding ladder
work: an ungrounded model cannot guess SM-1…SM-5, because it is invented.
"""
from __future__ import annotations

from pathlib import Path

from .numismatica_records import Lot
from ..markdown import write_md
from ..pdf import write_pdf


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_rules(config: dict, out_dir: Path) -> Path:
    c, sale = config, config["sale"]
    blocks: list[tuple[str, str]] = [
        ("title", f"{_esc(c['display_name'])} — Regolamento interno di catalogazione"),
        ("subtitle", f"Edizione in vigore per {_esc(sale['code'])} — {_esc(sale['title'])}. {_esc(c['city'])}."),
        ("h2", "1. Scala di conservazione interna"),
        ("body",
         "La casa d'aste adotta una scala interna a cinque livelli, denominata "
         "<b>scala SM</b>, applicata a ogni lotto prima della pubblicazione. La "
         "scala non è convertibile automaticamente in altre scale di mercato: "
         "ogni conversione richiede il parere del perito."),
    ]
    for g in c["grades"]:
        blocks.append(("field", f"<b>{_esc(g['code'])} — {_esc(g['label'])}</b>: {_esc(g['definition'])}"))

    blocks += [
        ("h2", "2. Campi obbligatori in ogni scheda di lotto"),
        ("body", "Nessuna scheda può essere pubblicata se manca anche uno solo dei campi seguenti:"),
    ]
    for i, f in enumerate(c["mandatory_fields"], 1):
        blocks.append(("field", f"{i}. {_esc(f)}"))

    blocks += [("h2", "3. Regole di redazione")]
    for i, r in enumerate(c["house_rules"], 1):
        blocks.append(("field", f"3.{i} {_esc(r)}"))

    blocks += [
        ("h2", "4. Responsabilità"),
        ("body",
         "La responsabilità finale dell'attribuzione resta in capo al perito "
         "numismatico della casa d'aste. Strumenti automatici possono produrre "
         "bozze, mai attribuzioni definitive."),
    ]
    write_md(out_dir / "regolamento-catalogazione.md", blocks)
    return write_pdf(out_dir / "regolamento-catalogazione.pdf", blocks)


def build_grading_guide(config: dict, out_dir: Path) -> Path:
    blocks: list[tuple[str, str]] = [
        ("title", "Guida rapida alla scala SM"),
        ("subtitle", "Promemoria operativo per lo staff. Estratto del regolamento, sezione 1."),
        ("body",
         "In caso di dubbio fra due livelli adiacenti si assegna sempre il "
         "livello <b>inferiore</b>. Il dubbio va annotato nel campo note."),
    ]
    for g in config["grades"]:
        blocks += [
            ("h2", f"{_esc(g['code'])} — {_esc(g['label'])}"),
            ("body", _esc(g["definition"])),
        ]
    blocks += [
        ("h2", "Errori frequenti"),
        ("field", "• Assegnare SM-1 per una patina attraente: la patina non compensa l'usura."),
        ("field", "• Usare SM-5 come sinonimo di 'danneggiata': SM-5 indica valore documentale."),
        ("field", "• Omettere il grado quando l'attribuzione è incerta: i due campi sono indipendenti."),
    ]
    write_md(out_dir / "guida-scala-conservazione.md", blocks)
    return write_pdf(out_dir / "guida-scala-conservazione.pdf", blocks)


def lot_blocks(lot: Lot, config: dict) -> list[tuple[str, str]]:
    sale = config["sale"]
    return [
        ("title", f"Lotto {lot.number:03d} — {_esc(lot.denomination)}"),
        ("subtitle", f"{_esc(sale['code'])} — {_esc(sale['title'])} · {sale['date']}"),
        ("field", f"<b>Riferimento interno di lotto</b>: {_esc(lot.reference)}"),
        ("field", f"<b>Nominale</b>: {_esc(lot.denomination)}"),
        ("field", f"<b>Autorità emittente</b>: {_esc(lot.authority)}"),
        ("field", f"<b>Zecca</b>: {_esc(lot.mint)}"),
        ("field", f"<b>Periodo</b>: {_esc(lot.period)}"),
        ("field", f"<b>Metallo</b>: {_esc(lot.metal)}"),
        ("field", f"<b>Peso</b>: {lot.weight_g:.2f} g"),
        ("field", f"<b>Diametro</b>: {lot.diameter_mm} mm"),
        ("field", f"<b>Asse di conio</b>: {_esc(lot.die_axis)}"),
        ("field", f"<b>Conservazione</b>: {_esc(lot.grade)} ({_esc(lot.grade_label)})"),
        ("spacer", "8"),
        ("h2", "Descrizione"),
        ("field", f"<b>Dritto</b>: {_esc(lot.obverse)}"),
        ("field", f"<b>Rovescio</b>: {_esc(lot.reverse)}"),
        ("field", f"<b>Legenda</b>: {_esc(lot.legend)}"),
        ("field", f"<b>Riferimento bibliografico</b>: {_esc(lot.catalogue_ref)}"),
        ("spacer", "8"),
        ("h2", "Provenienza e note"),
        ("field", _esc(lot.provenance)),
        ("field", _esc(lot.notes) if lot.notes else "—"),
        ("spacer", "10"),
        ("body", f"<font size=8 color='#6b7788'>Scheda redatta da {_esc(lot.operator)} — bozza non validata dal perito.</font>"),
    ]


def build_lot_sheets(lots: list[Lot], config: dict, out_dir: Path) -> list[Path]:
    return [
        write_pdf(out_dir / f"lotto-{lot.number:03d}.pdf", lot_blocks(lot, config))
        for lot in lots
    ]

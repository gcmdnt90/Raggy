# -*- coding: utf-8 -*-
"""Sector registry.

Each sector is one module with a shared interface, so adding a sector is a
Python module plus a JSON config and nothing else. The interface:

    SECTOR            dict: id, label, records_dir, poison_dir,
                      ground_truth_cols, record_noun
    build_records(config, rng) -> list[Record]
        Record is any dataclass with .number, .reference and .as_dict().
    build_house_docs(config, out_dir) -> list[Path]
        The invented internal scale and house rules. These MUST contain
        something no model can guess — that is what makes the M3 grounding
        ladder legible.
    record_blocks(record, config) -> list[tuple[str, str]]
        Blocks for markdown.write_md / pdf.write_pdf.
    poison_record(records, config) -> Record
        A plausible extra record to carry the hidden instruction (M5).
    demo_files(records, config) -> dict[filename, text]
        Paste-ready snippets for the earlier demos (M1, M2, M4).
"""
from __future__ import annotations

from . import (associazione, automazione, defi, fotovoltaico, maglieria,
               numismatica)

REGISTRY = {
    m.SECTOR["id"]: m for m in (numismatica, fotovoltaico, automazione,
                                 defi, associazione, maglieria)
}


def get(sector_id: str):
    if sector_id not in REGISTRY:
        raise KeyError(
            f"settore sconosciuto: {sector_id}. Disponibili: {', '.join(sorted(REGISTRY))}"
        )
    return REGISTRY[sector_id]

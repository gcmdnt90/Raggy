# -*- coding: utf-8 -*-
"""The M5 indirect prompt-injection document.

Safety stance for teaching material: the injected instruction must be
*read-only and harmless*. It asks the agent to list files and echo content —
enough to visibly derail the task and to be caught, with nothing destructive
and nothing that leaves the machine. Never demonstrate injection with an
instruction that deletes, sends, pays or publishes.

Sector-agnostic: the record and its layout come from the sector module.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .common import esc
from .pdf import write_pdf


def build_poisoned_set(records: list, config: dict, sector, clean_dir: Path,
                       out_dir: Path) -> Path:
    """Copy the clean sheets, then add one poisoned sheet among them."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = sector.SECTOR["file_stem"]
    for pdf in sorted(clean_dir.glob(f"{stem}-*.pdf")):
        shutil.copy2(pdf, out_dir / pdf.name)

    record = sector.poison_record(records, config)
    blocks = sector.record_blocks(record, config)
    # Placed after the visible content: a plausible position for text pasted in
    # from an external supplier's file, which is exactly how this happens in
    # real life.
    blocks += [("spacer", "14"), ("hidden", esc(config["poison"]["instruction"]))]
    return write_pdf(out_dir / f"{stem}-{record.number:03d}.pdf", blocks)

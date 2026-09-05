# -*- coding: utf-8 -*-
"""Numismatic auction house — sector module.

The record shape and the coin vocabulary live in numismatica_records.py; the
house documents and the sheet layout in numismatica_docs.py. This module is
the adapter the shared spine talks to, plus the two things the earlier demos
need: the triage attributes M2 argues over, and the raw notes M4 pastes.
"""
from __future__ import annotations

import random
from pathlib import Path

from ..common import (as_json, five_attributes_md, pick_tradeoff,
                      three_candidates_md)
from .numismatica_records import Lot, build_lots
from .numismatica_docs import (build_grading_guide, build_rules, lot_blocks)

SECTOR = {
    "id": "numismatica",
    "label": "Casa d'aste numismatica",
    "records_dir": "lotti",
    "poison_dir": "avvelenata",
    "record_noun": "schede di lotto",
    "file_stem": "lotto",
    "ground_truth_cols": [
        "number", "reference", "denomination", "authority", "mint", "metal",
        "weight_g", "diameter_mm", "die_axis", "grade", "catalogue_ref",
        "rarity", "expected_demand", "attribution_certain", "operator",
    ],
}

# M2 argues over rarity, condition and expected demand. Condition is in the
# house scale already; expected demand is invented here, deliberately and
# declared as invented in the README - the same stance the SM scale takes.
#
# Rarity is NOT invented: C / NC / R / R2 / R3 is the ordinary Italian trade
# convention (Gigante, Montenegro and the dealer catalogues that follow them).
# Sorting the strings sorts the scale, which is what _cover_candidates relies
# on. Do not renumber it as R1...R5 - "R1" is not a grade anyone writes.
RARITY = ["C — comune", "NC — non comune", "R — rara",
          "R2 — molto rara", "R3 — estremamente rara"]
DEMAND = ["bassa", "media", "alta"]


def build_records(config: dict, rng: random.Random) -> list[Lot]:
    lots = build_lots(config, rng)
    for lot in lots:
        lot.rarity = rng.choice(RARITY)
        lot.expected_demand = rng.choice(DEMAND)
    return lots


def build_house_docs(config: dict, out_dir: Path) -> list[Path]:
    return [build_rules(config, out_dir), build_grading_guide(config, out_dir)]


def record_blocks(lot: Lot, config: dict):
    return lot_blocks(lot, config)


def poison_record(records: list[Lot], config: dict) -> Lot:
    cfg = config["poison"]
    n = cfg["lot_number"]
    # The poisoned sheet has to survive the same expert eye as the others: its
    # denomination, metal, weight and diameter are taken from one real type in
    # the config, never assembled by hand. A bronze Grosso of 9.4 g is spotted
    # in two seconds and discredits the whole demo.
    coin = next(t for t in config["types"] if t["metal"] == "Bronzo")
    lot = Lot(
        number=n,
        reference=f"ART-{config['sale']['date'][:4]}-{n:03d}",
        denomination=coin["denomination"],
        authority="NON DETERMINATO",
        period="NON DETERMINATO",
        mint="NON DETERMINATO",
        metal=coin["metal"],
        weight_g=round(sum(coin["weight"]) / 2, 2),
        diameter_mm=round(sum(coin["diameter"]) / 2, 1),
        die_axis="NON RILEVATO",
        grade="SM-4",
        grade_label="Modesta",
        obverse="Busto radiato a destra, corazzato",
        reverse="Figura stante a sinistra, attributi illeggibili",
        legend="[illeggibile]",
        catalogue_ref="NON DETERMINATO",
        provenance="PROVENIENZA NON DOCUMENTATA",
        attribution_certain=False,
        operator="—",
        notes="Scheda acquisita da fornitore esterno.",
    )
    lot.rarity = "NC — non comune"
    lot.expected_demand = "bassa"
    return lot


def _cover_candidates(records: list[Lot]) -> list[Lot]:
    """Three candidates for the catalogue cover.

    House rule 3.3 forbids SM-5 on the cover, so the excluded grade is filtered
    out here: the argument M2 asks for has to be winnable on the merits, not on
    a rule the room has not been told yet.
    """
    eligible = [l for l in records if l.grade != "SM-5"]
    demand_rank = {"alta": 2, "media": 1, "bassa": 0}
    return pick_tradeoff(
        eligible,
        [lambda l: l.rarity,                                    # the rarest
         lambda l: (-int(l.grade.split("-")[1]), l.rarity),      # best preserved
         lambda l: (demand_rank.get(l.expected_demand, 0), l.rarity)],
        lambda l: (l.rarity, l.grade, l.expected_demand))


def demo_files(records: list[Lot], config: dict) -> dict[str, str]:
    pick = next((l for l in records if l.attribution_certain and l.metal == "Argento"),
                records[0])
    five = five_attributes_md(
        f"Lotto {pick.number:03d} — cinque attributi",
        [("Metallo", pick.metal),
         ("Peso", f"{pick.weight_g} g"),
         ("Conservazione", f"{pick.grade} ({pick.grade_label})"),
         ("Rarità", pick.rarity),
         ("Domanda attesa", pick.expected_demand)],
        "Da incollare al posto di `[INCOLLA 5 ATTRIBUTI]` in `m2-p1`.",
    )
    cands = _cover_candidates(records)
    three = three_candidates_md(
        "Tre lotti per la copertina",
        "Da mostrare con `m2-p2`. Il regolamento (3.3) esclude gli SM-5 dalla copertina: "
        "i tre candidati sono già filtrati.",
        ["Rarità", "Conservazione", "Domanda attesa"],
        [{"label": f"Lotto {l.number:03d} — {l.denomination}",
          "Rarità": l.rarity,
          "Conservazione": f"{l.grade} ({l.grade_label})",
          "Domanda attesa": l.expected_demand} for l in cands],
    )
    raw = records[min(6, len(records) - 1)]
    grezzi_md = "\n".join([
        f"{config['sale']['code']} — lotto {raw.number:02d}",
        "",
        f"{raw.denomination.lower()} {raw.metal.lower()}",
        f"peso {str(raw.weight_g).replace('.', ',')} g (bilancia da banco, da ricontrollare)",
        f"diametro ~{int(raw.diameter_mm)} mm",
        "asse di conio: non rilevato",
        f"dritto: {raw.obverse.lower()}, legenda parzialmente leggibile",
        f"rovescio: {raw.reverse.lower()}",
        f"conservazione: {raw.grade_label.lower()}, rilievi ancora netti sui punti alti",
        "riferimento bibliografico: ?",
        f"{raw.provenance.lower()}",
        "zecca e anno: non determinati",
        "",
    ])
    grezzi_json = as_json({
        "asta": config["sale"]["code"],
        "lotto": raw.number,
        "metallo": raw.metal,
        "peso_g": raw.weight_g,
        "peso_nota": "bilancia da banco, da ricontrollare",
        "diametro_mm": raw.diameter_mm,
        "dritto": raw.obverse,
        "rovescio": raw.reverse,
        "conservazione_nota": raw.grade_label,
        "riferimento_bibliografico": None,
        "asse_di_conio": None,
        "provenienza": raw.provenance,
        "zecca": None,
        "anno": None,
    })
    return {
        "m2-cinque-attributi.md": five,
        "m2-tre-candidati.md": three,
        "m4-grezzi.md": grezzi_md,
        "m4-grezzi.json": grezzi_json,
    }

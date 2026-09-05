#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the synthetic documents the lesson demos run on.

    python generate.py                                   # numismatica
    python generate.py --settore fotovoltaico
    python generate.py --settore automazione --out /some/where --seed 7
    python generate.py --settore numismatica \
        --nome "Casa d'Aste Artemide" \
        --out ../../engagements/smi/pilot-artemide/demo-data

The kit is organised by SECTOR, never by client: config/<settore>.json holds a
neutral synthetic company, and a real engagement supplies its own name and
output directory on the command line. Client names live in engagements/.

Output layout (see README.md for which demo uses what):

    <out>/
      LEGGIMI-SINTETICO.md
      regole/        house rules + scale guide           -> M3 rungs 2-3
                     .md is the source of truth (both rungs read it);
                     .pdf is the printable mirror
      <records>/     the sector's sheets                 -> M4 folder task
      avvelenata/    same sheets + one poisoned one      -> M5 injection
      demo/          paste-ready snippets                -> M1, M2, M4
      _perito/       ground-truth CSV (trainer only)     -> M4 verification
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from generators.common import write_demo_files, write_ground_truth
from generators.poison import build_poisoned_set
from generators.settori import REGISTRY, get

HERE = Path(__file__).resolve().parent

READ_ME = """# Dati sintetici per la lezione — {name}

**Nessuno di questi documenti è reale.** Sono generati automaticamente per una
dimostrazione didattica. La scala interna e il regolamento sono **inventati**:
servono a rendere evidente quando un modello risponde davvero a partire dai
vostri documenti e quando sta improvvisando. Sono inventati anche i campi di
giudizio usati nel modulo 2 — dove il criterio non è misurabile dal documento,
il valore è sintetico e va trattato come tale.

| Cartella | Contenuto | Usata in |
|---|---|---|
| `regole/` | regolamento interno e guida alla scala (`.md` + `.pdf`) | M3 — grounding |
| `{records}/` | {n} {noun} in PDF | M4 — compito su cartella |
| `avvelenata/` | le stesse schede + una con istruzione nascosta | M5 — prompt injection |
| `demo/` | ritagli pronti da incollare | M1, M2, M4 |
| `_perito/` | risposte corrette (CSV) | M4 — verifica, **solo per il docente** |

Non puntare l'agente su `_perito/`: contiene le risposte.

La scheda `avvelenata/{stem}-{poison:03d}.pdf` contiene un'istruzione nascosta
in grigio chiarissimo, corpo 4,6. È volutamente innocua: chiede solo di
elencare file. Aprire il PDF e selezionare tutto il testo per mostrarla alla
platea.

Rigenerare con: `python generate.py --settore {sector}` (stesso seed → stessi
documenti).
"""


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def resolve_out(config: dict, cli_out: str | None, config_path: Path) -> Path:
    if cli_out:
        return Path(cli_out).expanduser().resolve()
    return (config_path.parent / config["output"]).resolve()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--settore", default="numismatica", choices=sorted(REGISTRY),
                    help="quale settore generare")
    ap.add_argument("--config", default=None,
                    help="config esplicita (default: config/<settore>.json)")
    ap.add_argument("--nome", default=None,
                    help="nome dell'azienda da stampare sui documenti (per un cliente reale)")
    ap.add_argument("--out", default=None, help="cartella di uscita")
    ap.add_argument("--seed", type=int, default=None, help="sovrascrive il seed della config")
    args = ap.parse_args(argv)

    sector = get(args.settore)
    config_path = Path(args.config).resolve() if args.config \
        else (HERE / "config" / f"{args.settore}.json")
    if not config_path.exists():
        print(f"config non trovata: {config_path}", file=sys.stderr)
        return 1

    config = load_config(config_path)
    if args.nome:
        config["display_name"] = args.nome
    out = resolve_out(config, args.out, config_path)
    rng = random.Random(args.seed if args.seed is not None else config["seed"])

    spec = sector.SECTOR
    rules_dir = out / "regole"
    records_dir = out / spec["records_dir"]
    poison_dir = out / spec["poison_dir"]
    demo_dir = out / "demo"
    key_dir = out / "_perito"

    records = sector.build_records(config, rng)
    sector.build_house_docs(config, rules_dir)

    from generators.pdf import write_pdf
    sheets = [write_pdf(records_dir / f"{spec['file_stem']}-{r.number:03d}.pdf",
                        sector.record_blocks(r, config)) for r in records]
    build_poisoned_set(records, config, sector, records_dir, poison_dir)
    key = write_ground_truth(records, spec["ground_truth_cols"], key_dir)
    demo_written = write_demo_files(sector.demo_files(records, config), demo_dir)

    out.mkdir(parents=True, exist_ok=True)
    (out / "LEGGIMI-SINTETICO.md").write_text(
        READ_ME.format(name=config["display_name"], n=len(sheets),
                       records=spec["records_dir"], noun=spec["record_noun"],
                       stem=spec["file_stem"], sector=spec["id"],
                       poison=config["poison"]["lot_number"]),
        encoding="utf-8")

    print(f"→ {out}   [{spec['label']}]")
    print(f"  regole/       2 documenti (.md per i gradini M3, .pdf come copia stampabile)")
    print(f"  {spec['records_dir']+'/':<13} {len(sheets)} schede")
    print(f"  avvelenata/   {len(sheets) + 1} schede (1 con istruzione nascosta: n. {config['poison']['lot_number']})")
    print(f"  demo/         {len(demo_written)} ritagli per M1/M2/M4")
    print(f"  _perito/      {key.name}  ← risposte, non mostrare all'agente")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Synthetic demo data

Generates the documents the lesson demos run on. Organised **by sector, never
by client**: `config/<settore>.json` describes a neutral synthetic company, and
a real engagement supplies its own name and output directory on the command
line. Client names live in `engagements/`, not here.

Six sectors, matching the deck's sector selector:

| `--settore` | Sector | Record | Invented scale |
|---|---|---|---|
| `numismatica` | numismatic auction house | lot sheet | **SM-1 … SM-5** condition |
| `fotovoltaico` | PV monitoring & optimisation | monthly performance sheet | **RG-1 … RG-5** yield class |
| `automazione` | industrial automation software | test protocol sheet | **CE-1 … CE-5** outcome class |
| `defi` | blockchain software house / DeFi protocol | release sheet | **RD-1 … RD-5** release risk |
| `associazione` | trade association, member advice desk | member query sheet | **UA-1 … UA-5** response class |
| `maglieria` | production-software house for knitwear | specification sheet | **SP-1 … SP-5** specification class |

> **Document shape is researched, values are not.** `RICERCA-DATI.md` records
> what each trade's working document really contains — fields, order, code
> formats, the blanks it habitually leaves — with a source for every claim, and
> what changed in the configs because of it. Read it before altering a field:
> several of them are there because a professional would miss them in seconds.

Nothing produced here is real. The house rules and the internal scale are
invented on purpose — that is what makes the Module 3 grounding ladder work.
An ungrounded model cannot guess an invented scale, so the difference between
rung 1 (plain chat, fluent and wrong) and rungs 2–3 (grounded, correct) is
visible to a room that knows nothing about AI. The judgement fields Module 2
argues over (rarity and expected demand, client urgency, line downtime) are
invented for the same reason and declared as invented in the generated
`LEGGIMI-SINTETICO.md`.

## Run it

Windows (PowerShell), from this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python generate.py --settore numismatica
```

macOS / Linux:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python generate.py --settore numismatica
```

Options: `--settore <id>`, `--nome "<azienda>"`, `--out <dir>`, `--seed <int>`,
`--config <file>`. Same config + same seed → byte-identical documents, so a
demo rehearsed on Monday behaves identically on Friday.

For a real engagement, keep the sector config and override the two things that
are client-specific:

```bash
python generate.py --settore numismatica \
  --nome "<ragione sociale del cliente>" \
  --out ../../engagements/smi/<cartella-ingaggio>/demo-data
```

## What it produces

Default output: `delivery/demo-data/<settore>/`

| Folder | Contents | Used by |
|---|---|---|
| `regole/` | house rules + scale guide, `.md` **and** `.pdf` | **M3** — Project, Raggy, Ollama |
| `lotti/` `schede/` `collaudi/` `rilasci/` `quesiti/` `specifiche/` | 12 record sheets (PDF) | **M4** — the folder task |
| `avvelenata/` | the same sheets + one poisoned one | **M5** — prompt injection |
| `demo/` | paste-ready snippets | **M1, M2, M4** |
| `_perito/` | `ground-truth.csv` | **M4** — verification, trainer only |

### `demo/` — continuity across the modules

One sale, one month, one commissioning run feeds every demo, so M1's object,
M2's five attributes, M3's scale, M4's catalogue and M5's poisoned folder all
talk about the same records. Without this, each demo invented its own facts
and the lesson read as five unrelated toys.

| File | Fills | In |
|---|---|---|
| `m2-cinque-attributi.md` | `[INCOLLA 5 ATTRIBUTI]` | `m2-p1` |
| `m2-tre-candidati.md` | the three candidates to argue over | `m2-p2` |
| `m4-grezzi.md` / `.json` | `[INCOLLA DATI GREZZI]` | `m4-p1`, `m4-p3`, `m4-p9` |

The three candidates are chosen one per criterion, so they genuinely disagree:
three records where the same one wins on everything would make M2's argument a
formality. `m4-grezzi.*` describes a record that **is** in the sheets folder
and in `ground-truth.csv`, so the paste step, the folder task and the
verification step are about the same object.

## Why `regole/` is Markdown

Module 3 is a controlled comparison: rung 2 (Claude Project) and rung 3
(Raggy) must read **the same bytes**. If one gets a PDF and the other an
`.md`, extraction quality becomes a hidden variable and the room cannot tell
whether the difference it sees comes from the mechanism or from the file
format. So `regole/*.md` is the source of truth and both rungs load it; the
`.pdf` is the printable mirror, for anything that has to look like a document.

The record sheets and `avvelenata/` stay PDF: M4 needs real extraction, and M5
needs a PDF to hide text in.

**Never point the agent at `_perito/`.** It holds the answers, and the whole
value of the verification step is checking the agent's table against something
it could not read.

## The poisoned document

The extra sheet in `avvelenata/` carries an instruction in 4.6 pt, near-white
text, placed after the visible content — where text pasted from an external
supplier's file would plausibly sit.

The instruction is **read-only and harmless by design**: it asks the agent to
list files and echo content. It derails the task visibly and can be caught,
with nothing destructive, nothing irreversible, and nothing that leaves the
machine.

> Teaching material must never demonstrate injection with an instruction that
> deletes, sends, pays or publishes. The lesson is the hijack, not the damage.

To reveal it on screen: open the PDF and press Ctrl+A. The hidden line
highlights.

## Adding a sector

1. Write `generators/settori/<settore>.py` against the contract documented in
   `generators/settori/__init__.py`: `SECTOR`, `build_records`,
   `build_house_docs`, `record_blocks`, `poison_record`, `demo_files`.
2. Register it in the `REGISTRY` tuple in the same `__init__.py`.
3. Copy a config to `config/<settore>.json` and replace the business content:
   `display_name`, `sale`, `grades`, `mandatory_fields`, `house_rules`,
   `operators`, `output`.
4. Keep the internal scale **invented and distinctive**. A real, guessable
   scale destroys the demo — the ungrounded rung would answer correctly.
5. Add a `CHAIN` block in `generate_chain.py` — the trade nouns, the four
   plausible-but-wrong values a model invents for each hole, the industry
   answer rung 1 gives and why it is wrong, and the D5 human-verification list.
   Add any new table column to the `labels` map and the `keys` tuple in `d4()`.
6. Add a `sectors[]` entry **and about thirty `variants[]` texts in two
   languages** to `theory-deck/demo-prompts.json`. This is the part that is
   always underestimated: every prompt carries its own per-sector wording, and
   a missing variant falls back silently to another sector's phrasing.

**No real people, and no people at all.** Operators are **codes** (`REV-02`,
`COL-01`) — not names, not initials. A plausible local surname on a projected
sheet is indistinguishable from a real one, and in a small country it will
sometimes be the surname of somebody in the room; initials are only marginally
better. A code is what an anonymised internal export actually carries, so the
document shape survives and the sheet names nobody.

If you do not know enough about the client's business to fill the config
honestly, **ask them** — do not invent operational detail. The same rule as
`theory-deck/PROMPTS.md`: a plausible invented business fact will be
discovered live, by the one person in the room who knows it is wrong. The
sector configs shipped here are deliberately generic: a real engagement
refines them with facts the client supplied.

## Layout

```
generate.py                       CLI entry point
config/<settore>.json             everything sector-specific
generators/
  common.py                       escaping, ground truth, demo snippets,
                                  the standard house-documents shape
  pdf.py  markdown.py             rendering helpers (shared)
  poison.py                       the M5 injection document (sector-agnostic)
  settori/
    __init__.py                   registry + the sector contract
    numismatica.py                adapter, triage fields, demo snippets
    numismatica_records.py        lot records (deterministic)
    numismatica_docs.py           catalogue rules, grading guide, lot sheets
    fotovoltaico.py               records, documents, snippets
    automazione.py                records, documents, snippets
    defi.py                       records, documents, snippets
    associazione.py               records, documents, snippets
    maglieria.py                  records, documents, snippets
```

PDFs are deliberately plain — no tables, no columns, no images — so text
extraction is clean for whatever tool reads them.

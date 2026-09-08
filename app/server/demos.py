"""Read the demo database and resolve it for a sector.

The database is `demo/demo-prompts.json`, vendored from the theory-deck at the
commit in `demo/DECK-PIN.txt`. It is the single source of truth for prompt text,
shared with the deck. Never hard-code a prompt here. See docs/adr/0001.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "demo" / "demo-prompts.json"

# Fields that exist for the trainer and must never reach the harness.
# `theory-deck/PROMPTS.md` names `lands`, `watch_for` and `note` as
# speaker-notes-only; `limits` was confirmed trainer-facing on 2026-09-05 (it is
# a reminder to the trainer about what a given product does or does not expose).
# Do not widen this set without confirming the field's audience.
TRAINER_FIELDS = {
    "lands", "lands_it",
    "watch_for", "watch_for_it",
    "note", "note_it",
    "limits", "limits_it",
}

_PLACEHOLDER = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(DB_PATH.read_text(encoding="utf-8"))


def sectors() -> list[dict]:
    """Sector ids are English (`numismatics`); the data folders are Italian.

    The mapping is in the database, not here: `sector.data.folder` gives the
    folder under `demo/data/`, `sector.data.records_dir` the records folder D4
    works over. Never hard-code either.
    """
    return [
        {
            "id": s["id"],
            "label": s.get("label"),
            "label_it": s.get("label_it"),
            "folder": s.get("data", {}).get("folder"),
            "records_dir": s.get("data", {}).get("records_dir"),
        }
        for s in load().get("sectors", [])
    ]


def data_root(sector: str) -> Path:
    """Absolute path to this sector's demo material."""
    folder = next(
        (s.get("data", {}).get("folder") for s in load().get("sectors", []) if s["id"] == sector),
        None,
    )
    if folder is None:
        raise KeyError(sector)
    return DB_PATH.parent / "data" / folder


def list_demos() -> list[dict]:
    return [
        {
            "id": d.get("id"),
            "title": d.get("title"),
            "title_it": d.get("title_it"),
            "shape": d.get("shape"),
            "minutes": d.get("minutes"),
        }
        for d in load().get("demos", [])
    ]


def _substitute(text: str, client: dict) -> str:
    return _PLACEHOLDER.sub(lambda m: str(client.get(m.group(1), m.group(0))), text)


def resolve_demo(demo_id: str, sector: str) -> dict:
    """One demo, resolved for `sector` and safe to render on the projected surface.

    Three things happen here, in this order, and all three happen once so that no
    route can skip one by forgetting:

    1. **Variants applied.** A node carrying `variants` has `variants[sector]`
       merged over it. This is how a prompt becomes sector-specific; placeholder
       substitution alone is not enough.
    2. **Placeholders substituted** from the sector's `client` block.
    3. **Trainer material removed** - the fields in TRAINER_FIELDS, and any entry
       in a `files` list flagged `trainer: true`, which the deck already uses to
       keep a file off the projected download rail.

    See AGENTS.md rules 2 and 4.
    """
    db = load()
    sec = next((s for s in db.get("sectors", []) if s["id"] == sector), None)
    if sec is None:
        raise KeyError(sector)
    client = sec.get("client", {})

    demo = next((d for d in db.get("demos", []) if d.get("id") == demo_id), None)
    if demo is None:
        raise KeyError(demo_id)

    def resolve(node):
        if isinstance(node, dict):
            if "variants" in node:
                merged = {k: v for k, v in node.items() if k != "variants"}
                merged.update(node["variants"].get(sector, {}))
                node = merged
            out = {}
            for k, v in node.items():
                if k in TRAINER_FIELDS:
                    continue
                if k == "files" and isinstance(v, list):
                    v = [f for f in v if not (isinstance(f, dict) and f.get("trainer"))]
                out[k] = resolve(v)
            return out
        if isinstance(node, list):
            return [resolve(v) for v in node]
        if isinstance(node, str):
            return _substitute(node, client)
        return node

    return resolve(demo)


# TODO(M1): a `run` block per beat — panes, provider/model per pane, temperature,
#   thinking level, input files, expected artefact. Additive to the schema so the
#   deck ignores it. See docs/adr/0001.

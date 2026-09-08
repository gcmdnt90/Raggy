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
TRAINER_FIELDS = {"lands", "watch_for", "note", "lands_it", "watch_for_it", "note_it"}

_PLACEHOLDER = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(DB_PATH.read_text(encoding="utf-8"))


def sectors() -> list[dict]:
    return [
        {"id": s["id"], "label": s.get("label"), "label_it": s.get("label_it")}
        for s in load().get("sectors", [])
    ]


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
    """Return one demo with placeholders substituted and trainer fields stripped.

    Stripping happens here, once, so no route can leak a trainer field by
    forgetting to. See AGENTS.md rule 2.
    """
    db = load()
    client = next(
        (s.get("client", {}) for s in db.get("sectors", []) if s["id"] == sector), {}
    )
    demo = next((d for d in db.get("demos", []) if d.get("id") == demo_id), None)
    if demo is None:
        raise KeyError(demo_id)

    def clean(node):
        if isinstance(node, dict):
            return {k: clean(v) for k, v in node.items() if k not in TRAINER_FIELDS}
        if isinstance(node, list):
            return [clean(v) for v in node]
        if isinstance(node, str):
            return _substitute(node, client)
        return node

    return clean(demo)


# TODO(M1): a `run` block per beat — panes, provider/model per pane, temperature,
#   thinking level, input files, expected artefact. Additive to the schema so the
#   deck ignores it. See docs/adr/0001.

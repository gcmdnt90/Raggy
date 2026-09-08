"""The harness — the projected surface.

INVARIANT: nothing rendered here may contain an API key or a client name, and
nothing here may render `_perito/ground-truth.csv`, `LEGGIMI-*.md`, or a trainer
note. Those belong to the console. See AGENTS.md rule 2.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.server.demos import list_demos, resolve_demo

router = APIRouter()
PAGE = Path(__file__).resolve().parent.parent / "web" / "harness" / "index.html"


@router.get("/")
def index() -> FileResponse:
    return FileResponse(PAGE)


@router.get("/api/demos")
def demos() -> list[dict]:
    """Demo list for the selector: id, title, shape, minutes. No trainer fields."""
    return list_demos()


@router.get("/api/demos/{demo_id}")
def demo(demo_id: str, sector: str) -> dict:
    """One demo with placeholders resolved for `sector`. No trainer fields."""
    return resolve_demo(demo_id, sector)


# TODO(M1): POST /api/run  -> Server-Sent Events, one stream per pane.
#   Each event carries: pane index, delta, and the metadata the room must see —
#   provider, model, temperature, thinking budget, token counts, egress target.
#   See PROJECT.md objective 2 and milestone M1.
# TODO(M3): GET /api/replay/{recording_id} -> the same event shape from disk,
#   flagged `replayed: true` so the indicator renders. See ADR 3 (framework).

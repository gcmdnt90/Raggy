"""The harness — the projected surface.

INVARIANT: nothing rendered here may contain an API key or a client name, and
nothing here may render `_perito/ground-truth.csv`, `LEGGIMI-*.md`, or a trainer
note. Those belong to the console. See AGENTS.md rule 2.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.i18n import DEFAULT_LANGUAGE, localized
from app.server import preflight, runner, sources
from app.server.demos import list_demos, resolve_demo, sectors
from app.server.runs import build_prompt, run_block, unblocked_reason
from app.server.runs import plan as build_plan

router = APIRouter()
PAGE = Path(__file__).resolve().parent.parent / "web" / "harness" / "index.html"


class RunRequest(BaseModel):
    """What the harness asks to run. Never a prompt - only which beat.

    `language` defaults to Banco's default rather than to English. The page
    always sends the field, so the default is only reached by something that
    is not the page - a script, a test, a future console rehearsal button -
    and until 2026-09-13 that default was `"en"`, which would have run an
    Italian lesson's beat against the English prompt. AGENTS.md rule 9 says
    Italian first; there is no second place in Banco where the default is
    anything else.
    """

    demo_id: str = Field(min_length=1, max_length=32)
    beat_id: str = Field(min_length=1, max_length=64)
    sector: str = Field(min_length=1, max_length=64)
    language: str = Field(default=DEFAULT_LANGUAGE, pattern="^(en|it)$")


@router.get("/harness")
def index() -> FileResponse:
    """The projected surface, on its own path.

    It used to live at `/`, which now serves pre-flight: every lesson starts
    with a check, not only the first one. `/harness` is the URL to put on the
    projector - and the only one that is safe to, since `/` shows key fields.
    """
    return FileResponse(PAGE)


@router.get("/api/sectors")
def api_sectors() -> list[dict]:
    """Sector ids and labels, each marked with whether its material is on disk.

    Never the client block: that carries a real name. Readiness is not a
    credential and belongs here - a trainer picking a sector whose pack was
    never generated should see that before pressing Run, not as a missing-file
    error in front of a room.
    """
    ready = {s["id"]: s for s in preflight.sectors_overview()}
    out = []
    for sector in sectors():
        state = ready.get(sector["id"], {})
        out.append(sector | {
            "ready": state.get("ready", False),
            "missing_demos": state.get("missing_demos", []),
        })
    return out


@router.get("/api/status")
def api_status() -> dict:
    """Profile and per-role source. Provider, model and egress host only.

    No credential state of any kind, not even whether a key is present - that
    belongs to the stage console's pre-flight.
    """
    return sources.status(get_settings())


@router.get("/api/demos")
def demos() -> list[dict]:
    """Demo list for the selector: id, title, shape, minutes. No trainer fields."""
    return list_demos()


def _prompt_preview(
    beat: dict, block: dict | None, sector: str, lang: str | None
) -> tuple[str, bool]:
    """The prompt this beat will send, composed before anyone presses Run.

    The harness panel is labelled *il prompt come inviato* and until 2026-09-13
    it held the template: the paste placeholder was only expanded at run time,
    inside `runs.build_prompt`, and reached the page on the `plan` event. So a
    room looking at that panel before the run read `[PASTE RAW NOTES]` where
    the notes go, under a label promising it was what got sent. Objective 2
    says the prompt is visible *as sent*; a template under that label is the
    panel making a false claim on a projected screen.

    `build_prompt` is pure and reads the same files the run reads, so the
    preview cannot disagree with what is sent - which is the same argument the
    capability check makes in `docs/specs/model-control.md`: answer by building
    the thing, not by consulting a second description of it.

    Returns the text and whether it is complete. A beat Banco cannot run sends
    nothing, and a sector whose pack was never generated has no file to paste;
    both return the localized template and False, and the page relabels rather
    than claiming a placeholder is what leaves the machine.
    """
    template = localized(beat, "text", lang, default="")
    if block is None:
        return template, False
    try:
        return build_prompt(beat, block, sector, language=lang or DEFAULT_LANGUAGE), True
    except (FileNotFoundError, ValueError):
        # Missing pack, or a path that escapes the sector. Pre-flight is where
        # that gets reported; here it must not take the whole demo list down.
        return template, False


@router.get("/api/demos/{demo_id}")
def demo(demo_id: str, sector: str, lang: str | None = None) -> dict:
    """One demo with placeholders resolved for `sector`. No trainer fields.

    Each beat is annotated with whether Banco can execute it and, if not, the
    reason recorded in `run-blocks.json`. The trainer should never have to guess
    which beats are live, and the room should never watch one be attempted and
    silently do nothing.

    `lang` is not decoration. `teaches` and a blocked beat's reason are composed
    here from `run-blocks.json`, and the page has always asked for them with
    `?lang=` - but this signature did not accept the parameter, so FastAPI
    dropped it and both came back English into an Italian lesson. Absent means
    Italian, as everywhere else (AGENTS.md rule 9).
    """
    try:
        resolved = resolve_demo(demo_id, sector)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown demo or sector: {exc}") from exc

    for beat in resolved.get("prompts", []):
        block = run_block(beat.get("id"))
        prompt, complete = _prompt_preview(beat, block, sector, lang)
        beat["run"] = {
            "runnable": block is not None,
            "panes": len(block.get("panes", [])) if block else 0,
            "teaches": localized(block, "teaches", lang),
            "continues": block.get("continues") if block else None,
            "reason": None if block else unblocked_reason(beat.get("id"), lang),
            "prompt": prompt,
            "prompt_complete": complete,
        }
    return resolved


@router.post("/api/run")
def run(request: RunRequest) -> StreamingResponse:
    """Execute one beat across its panes, streaming the mechanism as it happens.

    POST rather than EventSource because the request carries a body, and the
    harness reads the stream with fetch. One stream per beat; panes are
    multiplexed on it and identified by index.
    """
    settings = get_settings()
    bound = sources.available_sources(settings)
    bound = {
        role: replace(
            s,
            temperature_applies=sources.temperature_applies(s.provider, s.model),
        )
        for role, s in bound.items()
    }
    credentials = {
        s.provider: sources.provider_kwargs(s.provider, settings) for s in bound.values()
    }

    try:
        plan = build_plan(
            request.demo_id,
            request.beat_id,
            request.sector,
            bound,
            language=request.language,
        )
    except KeyError as exc:
        # KeyError BEFORE LookupError: KeyError is a subclass of it, so the
        # other order reports an unknown beat as "exists but not executable".
        raise HTTPException(status_code=404, detail=f"unknown demo, beat or sector: {exc}") from exc
    except LookupError as exc:
        # The beat exists but is not executable. 409 rather than 404: the
        # resource is real, the state is wrong, and the body says why.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(
        runner.stream_beat(
            plan, max_tokens=settings.max_tokens, credentials=credentials
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Proxies must not buffer this: a buffered stream arrives as four
            # finished answers at once, which is the opposite of the point.
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/transcripts/reset")
def reset_transcripts() -> dict[str, str]:
    """Forget stored exchanges, so a rehearsal does not leak into the lesson.

    A beat marked `continues` interrogates what its pane said earlier. After a
    dry run those earlier answers are still in memory, and the room would watch
    a model be asked about an answer it gave before the lesson started.
    """
    runner.reset_transcripts()
    return {"status": "cleared"}


# TODO(M3): GET /api/replay/{recording_id} -> the same event shape from disk,
#   flagged `replayed: true` so the indicator renders. See ADR 3 (framework).
#   `pane_unavailable` already carries `would_replay` and a null `recording`,
#   which is the hook: fill it once recordings exist.

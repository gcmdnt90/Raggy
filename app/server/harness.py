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
    #: Per-role provider/model/reasoning chosen from the gear beside Esegui, for
    #: this run only. A *role* is overridden, never a pane: run blocks name
    #: roles and never providers (ADR 0003), and that indirection is what lets a
    #: source that disappears degrade the beat instead of breaking it.
    overrides: dict[str, dict] = Field(default_factory=dict)
    #: The prompt as the trainer edited it in the viewer, for this run only.
    #: Never written back to the demo database: that file is vendored from the
    #: deck at a pinned commit (ADR 0001), and an edit here that silently
    #: changed it would put Banco and the slides on two different texts.
    prompt_override: str | None = Field(default=None, max_length=200_000)


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


def _apply_overrides(
    bound: dict[str, sources.ModelSource], overrides: dict[str, dict]
) -> dict[str, sources.ModelSource]:
    """Rebind roles to the provider and model chosen at the gear.

    A role is rebound, never a pane, so `run-blocks.json` still names only roles
    and a beat still degrades when a source disappears (ADR 0003). An override
    naming a role the beat does not use changes nothing; an override naming a
    provider with no key produces a source that fails at the call and is
    narrated there, rather than being silently dropped here — the room is
    entitled to see that the thing the trainer selected did not answer.

    `think` is applied to the role's default params only. It cannot reach a
    pane whose run block states one, because `runs.pane_params` puts the run
    block first: m2-p2's two panes exist to contrast a budget against none, and
    a gear that flattened them would leave the beat running and teaching
    nothing.
    """
    if not overrides:
        return bound

    out = dict(bound)
    for role, choice in overrides.items():
        if not isinstance(choice, dict):
            continue
        current = out.get(role)
        provider = (choice.get("provider") or (current.provider if current else "")).strip()
        if not provider:
            continue
        model = (choice.get("model") or "").strip()
        base = sources.api_source(provider) if provider != "ollama" else current
        if base is None:
            base = sources.api_source(provider)
        params = dict(base.params)
        think = choice.get("think")
        if think in ("", None):
            params.pop("think", None)
        else:
            params["think"] = think
        out[role] = replace(base, model=model or base.model, params=params)
    return out


@router.get("/api/sources/catalogue")
def api_source_catalogue() -> dict:
    """What the gear may offer: configured providers and the models they list.

    No credential state and no key, not even a masked one — this is read by the
    projected page (invariant 1). "Configured" is as much as it says: whether a
    key actually works is the console's live check, which calls each source
    once and is the only thing entitled to claim it.

    Models come from the catalogue's cache or its static fallback, never from a
    live API call: this runs while a room is waiting and must not block on
    somebody's network.
    """
    from app.llm.providers import model_catalog

    settings = get_settings()
    out: list[dict] = []
    for provider in sources.configured_api_providers(settings):
        cached = model_catalog.cached(provider)
        models, live = cached if cached else (model_catalog.fallback(provider), False)
        out.append({
            "provider": provider,
            "models": list(models),
            "live": live,
            "egress": sources.API_EGRESS.get(provider, ""),
            "local": False,
        })

    local = sources.ollama_source(settings, check=False)
    if local is not None:
        try:
            from app.llm.providers.ollama import OllamaProvider

            local_models = OllamaProvider(base_url=settings.ollama_base_url).available_models()
        except Exception:  # noqa: BLE001 - Ollama absent is a normal state
            local_models = [local.model]
        out.append({
            "provider": "ollama",
            "models": local_models or [local.model],
            "live": bool(local_models),
            "egress": local.egress,
            "local": True,
        })
    return {"sources": out}


@router.get("/api/document")
def api_document(sector: str, path: str, lang: str | None = None) -> dict:
    """One of this sector's documents, as text, for the viewer.

    The room is asked to check an answer against the passages it was given, and
    a citation it cannot open is a citation it has to take on trust — which is
    the habit the whole lesson exists to break. Rooted on the sector and
    refusing trainer material in `corpus.read_document`, because that is the
    function that turns a path into a file read.
    """
    from app.server import corpus

    try:
        return {"path": path, "text": corpus.read_document(sector, path)}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (FileNotFoundError, KeyError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    bound = _apply_overrides(bound, request.overrides)
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
            prompt_override=request.prompt_override,
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

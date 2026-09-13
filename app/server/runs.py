"""Run blocks: what a program needs in order to execute a beat.

The prompt text lives in the vendored demo database (`app/server/demos.py`).
This module holds the other half - panes, model sources, sampling parameters,
pasted inputs - and merges the two at load time. See `docs/adr/0003`.

Nothing here contains prompt text, and nothing here names a provider. A pane
asks for a *role*; the configured profile binds roles to providers. That
indirection is what lets a missing source degrade a beat to replay rather than
remove it, which PROJECT.md requires of every beat.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from app.i18n import DEFAULT_LANGUAGE, localized, t
from app.server.demos import DB_PATH, data_root, resolve_demo

RUN_BLOCKS_PATH = DB_PATH.parent / "run-blocks.json"

Role = Literal["primary", "secondary", "local"]


def unavailable_no_source(lang: str | None = None) -> str:
    """Why a pane could not be bound.

    Carried to the harness so the room is told what is replayed and why, rather
    than shown a silently shorter demo — which means it is projected, which
    means it is translated. It was a module constant until Banco spoke two
    languages; a constant cannot be.
    """
    return t("runs.unavailable_no_source", lang)


@dataclass(frozen=True, slots=True)
class ModelSource:
    """One configured way to get a completion.

    `egress` is the host a call to this source reaches. It is carried through to
    the harness for every pane: without it the D5-A network-off gesture proves
    nothing, because the room never saw anything leave.
    """

    provider: str
    model: str
    egress: str
    local: bool = False
    #: False when this model ignores the temperature it is sent. Shown to the
    #: room, because "temperature 1.0" beside a model that discards it is a
    #: false statement on a projected screen.
    #:
    #: Superseded in substance by `ProviderRequest.dropped`, which answers the
    #: same question for every parameter rather than only this one. Kept for one
    #: release as the harness page's existing hook (docs/specs/model-control.md
    #: §6) and derived from the same source of truth.
    temperature_applies: bool = True
    #: Banco-vocabulary parameters this source carries by default, from the
    #: session profile. `compare=False` so a mutable field cannot make a frozen
    #: ModelSource unhashable — nothing here depends on the params for identity.
    params: dict = field(default_factory=dict, compare=False)


@dataclass(frozen=True, slots=True)
class Pane:
    """A resolved pane, ready to execute or explicitly unavailable."""

    pane: int
    label: str
    role: str
    temperature: float
    thinking: str | None = None
    source: ModelSource | None = None
    unavailable: str | None = None
    #: Everything this pane will send, after precedence has been applied. The
    #: single argument to `prepare()`; `temperature` and `thinking` above are
    #: views onto it kept for the existing harness payload.
    params: dict = field(default_factory=dict, compare=False)
    #: Which rung of D3's ladder this pane stands on: `none`, `all` or
    #: `retrieved`. Every other beat in Banco is `none`, which is why the
    #: default is the one that changes nothing.
    context: str = "none"
    #: The documents this pane puts in front of the question, already written.
    #: Composed at plan time and not in the pane's own thread: retrieval is I/O
    #: and a model load, the `plan` event carries it to the harness before any
    #: token streams, and a failure surfaces before the run rather than halfway
    #: through it.
    context_text: str = ""
    #: What rung 3 pulled back, as the harness renders it: source, score, text.
    #: Empty on every other rung — a pane showing no passages makes no claim
    #: about retrieval.
    passages: tuple[dict, ...] = field(default_factory=tuple, compare=False)

    @property
    def runnable(self) -> bool:
        return self.source is not None and self.unavailable is None


@dataclass(frozen=True, slots=True)
class RunPlan:
    """Everything needed to execute one beat, with nothing left to infer."""

    beat_id: str
    demo_id: str
    sector: str
    prompt: str
    panes: tuple[Pane, ...]
    continues: str | None = None
    produces: str | None = None
    teaches: str | None = None
    inputs: tuple[dict, ...] = field(default_factory=tuple)
    #: The parameters this beat exists to expose. They are what a collapsed
    #: pane shows without any gesture; everything else sits behind Info
    #: (docs/specs/model-control.md §2 and §6, cleared under AGENTS.md §7).
    #: Empty is legal and means "nothing to foreground" — the safe default,
    #: because a pane showing no parameter makes no claim about it.
    teaches_params: tuple[str, ...] = field(default_factory=tuple)
    #: Pasted files written in a language other than this run's. Not a refusal —
    #: the chain never waits — but the room is about to read them, so the
    #: trainer is told rather than left to notice mid-beat.
    language_mismatches: tuple[str, ...] = field(default_factory=tuple)
    degraded: bool = False
    #: The language this beat was planned in. Carried rather than re-derived so
    #: that whatever the run writes afterwards — the handover file above all —
    #: is in the same language as the prompt that was sent.
    language: str = DEFAULT_LANGUAGE

    @property
    def runnable_panes(self) -> tuple[Pane, ...]:
        return tuple(p for p in self.panes if p.runnable)


@lru_cache(maxsize=1)
def load_run_blocks() -> dict:
    """Read run-blocks.json. Missing file is an error, not an empty default.

    A silently empty set of run blocks would present as "this beat cannot run
    live" and send the lesson to replay, which is exactly the failure the file
    exists to prevent.
    """
    if not RUN_BLOCKS_PATH.is_file():
        raise FileNotFoundError(t("runs.run_blocks_missing", path=RUN_BLOCKS_PATH))
    import json

    return json.loads(RUN_BLOCKS_PATH.read_text(encoding="utf-8"))


def run_block(beat_id: str) -> dict | None:
    """The run block for `beat_id`, or None if the beat is not executable.

    None is a legitimate answer: library and archived beats deliberately have
    none, and the `_unblocked` map in the file records why for each.
    """
    return load_run_blocks().get("beats", {}).get(beat_id)


def unblocked_reason(beat_id: str, lang: str | None = None) -> str | None:
    """Why a beat has no run block, if the file says.

    The reason is rendered on the projected surface beside a beat the trainer
    cannot run, so `run-blocks.json` carries both languages: `_unblocked` in
    English and `_unblocked_it` in Italian, falling back to English when an
    entry has not been translated yet.
    """
    blocks = load_run_blocks()
    suffix = "_it" if str(lang or DEFAULT_LANGUAGE).startswith("it") else ""
    reason = blocks.get(f"_unblocked{suffix}", {}).get(beat_id)
    return reason or blocks.get("_unblocked", {}).get(beat_id)


def find_beat(demo_id: str, beat_id: str, sector: str) -> dict:
    """One beat from the resolved demo - variants applied, trainer fields gone.

    Goes through `resolve_demo` rather than reading the database directly, so a
    beat cannot reach a caller with trainer material still attached.
    """
    demo = resolve_demo(demo_id, sector)
    for beat in demo.get("prompts", []):
        if beat.get("id") == beat_id:
            return beat
    raise KeyError(beat_id)


#: The parameter names a run block pane may state directly. They are the same
#: four the providers speak (`app.llm.base.PARAM_NAMES`) — a pane cannot invent
#: a fifth, because a parameter no adapter translates would be a value on a
#: projected screen that no request ever carried.
PANE_PARAMS = ("temperature", "max_tokens", "system", "think")


def pane_params(spec: dict, source: ModelSource | None) -> dict:
    """Everything this pane will send, with precedence applied.

        run-block pane  >  profile demos.<demo_id>  >  profile defaults  >  provider default

    The order is the whole point and is tested in `tests/test_precedence.py`.
    `source.params` already carries the profile's answer for this demo — the
    per-demo override was merged over the defaults in `sessions.resolve` — so
    the only thing left to do here is let the run block win.

    **A parameter written on a pane in `run-blocks.json` is didactics.** It is
    what the beat exists to show, and no configuration may contradict it.
    Without this rule a session profile could quietly put D1's four panes at
    temperature 0.3: the demo would run, look correct, and teach nothing —
    which is exactly the failure Banco was built to end.
    """
    params = dict(source.params) if source else {}
    for name in PANE_PARAMS:
        if name in spec:
            params[name] = spec[name]
    return params


def pane_context(
    spec: dict, block: dict, sector: str | None, query: str, lang: str | None
) -> tuple[str, str, tuple[dict, ...], str | None]:
    """What this pane puts in front of the question — D3's three rungs.

    Returns `(strategy, text, passages, unavailable)`. The last one is the
    point: a rung that cannot be climbed makes *that pane* unavailable and
    leaves the others standing, so the room still sees the ladder and is told
    which rung did not run. Falling back to another rung would be the harness
    misrepresenting its own mechanism, which invariant 2 forbids more strongly
    than it forbids an empty pane.
    """
    strategy = spec.get("context", "none")
    if strategy == "none" or sector is None:
        return "none", "", (), None

    from app.server import corpus

    folder = (block.get("corpus") or {}).get("dir")
    try:
        if strategy == "all":
            body = corpus.all_documents_text(sector, folder)
            if not body:
                return strategy, "", (), t("corpus.no_documents", lang, sector=sector)
            return strategy, f"{t('corpus.all_heading', lang)}\n\n{body}", (), None

        if strategy == "retrieved":
            top_k = int((block.get("corpus") or {}).get("top_k", corpus.DEFAULT_TOP_K))
            found = corpus.retrieve(sector, query, top_k)
            if not found:
                return strategy, "", (), t("corpus.no_documents", lang, sector=sector)
            return (
                strategy,
                corpus.context_block(found, lang),
                tuple(p.as_dict() for p in found),
                None,
            )
    except (LookupError, FileNotFoundError, ValueError) as exc:
        # Named on the pane, in the room's language, instead of a 500 that
        # takes the whole beat down with it.
        return strategy, "", (), str(exc)

    return "none", "", (), None


def bind_panes(
    block: dict,
    sources: dict[str, ModelSource],
    *,
    lang: str | None = None,
    sector: str | None = None,
    query: str = "",
) -> tuple[Pane, ...]:
    """Bind each pane's role to a configured source, or mark it unavailable.

    `sources` maps role -> ModelSource and comes from the active session
    profile (`app.server.sessions.resolve`), or from the derived binding when
    there is none. A role with no source yields an unavailable pane carrying
    the reason; the caller degrades the beat rather than dropping the pane, so
    the room still sees four panes and is told which are replayed.
    """
    panes: list[Pane] = []
    for index, spec in enumerate(block.get("panes", [])):
        role = spec.get("role", "primary")
        source = sources.get(role)
        params = pane_params(spec, source)
        strategy, context_text, passages, context_problem = pane_context(
            spec, block, sector, query, lang
        )
        panes.append(
            Pane(
                pane=spec.get("pane", index),
                label=localized(
                    spec, "label", lang,
                    default=t("runs.pane_fallback_label", lang, index=index),
                ),
                role=role,
                # Kept as named fields for the existing harness payload; both
                # are now views onto `params`, which is what actually gets sent.
                temperature=float(params.get("temperature", 0.3)),
                thinking=params.get("think"),
                source=source,
                # No source first: a pane with nothing to run on cannot be
                # described as a rung that failed to load its documents.
                unavailable=(
                    unavailable_no_source(lang) if not source else context_problem
                ),
                params=params,
                context=strategy,
                context_text=context_text,
                passages=passages,
            )
        )
    return tuple(panes)


def read_input_file(relative_path: str, sector: str) -> str:
    """Read a pasted input, refusing to escape this sector's demo material.

    Paths in the demo database are relative to the SECTOR's data folder, not to
    `demo/`: `demo/m4-grezzi.md` means
    `demo/data/<sector folder>/demo/m4-grezzi.md`. The Italian folder name comes
    from the database via `demos.data_root`, never from a mapping written here.

    Paths come from a JSON file that ships with the repository rather than from
    a request, but this is the function that turns a string into a file read, so
    it is where the boundary check belongs - and rooting it per sector means one
    sector's beat cannot read another's material.
    """
    root = data_root(sector).resolve()
    target = (root / relative_path).resolve()
    if not target.is_relative_to(root):
        raise ValueError(t("runs.input_escapes_sector", path=repr(relative_path)))
    if not target.is_file():
        raise FileNotFoundError(t("runs.input_missing", path=target))
    return target.read_text(encoding="utf-8")


#: The marker `runner.write_chain_file` leaves at the top of every handover
#: file it writes. Read back by `chain_file_language`.
_LANGUAGE_MARKER = re.compile(r"<!--\s*banco:lang=([a-z]{2})\s*-->")


def chain_file_language(relative_path: str, sector: str) -> str | None:
    """The language a handover file was written in, if Banco wrote it.

    None for a file that ships with the repository: `demo/kit/generate_chain.py`
    produces the shipped fallbacks and does not mark them, and they are Italian
    because the demo material is. None therefore means "no claim", not "English".
    """
    try:
        text = read_input_file(relative_path, sector)
    except (OSError, ValueError):
        return None
    match = _LANGUAGE_MARKER.search(text[:512])
    return match.group(1) if match else None


def language_mismatches(block: dict, sector: str, language: str) -> tuple[str, ...]:
    """Pasted files this beat will use that were written in another language.

    The chain is five files, each produced by one demo and consumed by the next.
    Nothing stops a trainer running D1 in English during a rehearsal and D2 in
    Italian in the lesson — at which point `d1-bozze.md` holds English drafts and
    D2's Italian prompt says "queste quattro bozze" above them. The beat runs,
    the panes fill, and the room watches a model answer in whichever language it
    decides the request was in.

    Reported rather than refused: invariant 3 says the chain never waits. The
    trainer is told, on the console and beside the beat, and can re-run the
    earlier demo or carry on knowing why the material reads as it does.
    """
    mismatched: list[str] = []
    for spec in block.get("inputs", []):
        paste_file = spec.get("paste_file")
        if not paste_file:
            continue
        written_in = chain_file_language(paste_file, sector)
        if written_in is not None and written_in != language:
            mismatched.append(paste_file)
    return tuple(mismatched)


def build_prompt(
    beat: dict, block: dict, sector: str, *, language: str = DEFAULT_LANGUAGE
) -> str:
    """The prompt as it will be sent, with pasted files substituted in.

    Returns the text the room is entitled to see on screen: objective 2 says
    the system prompt *as sent* is visible, and that has to include whatever a
    paste placeholder expanded to.

    The language chosen here is the language the *model* is prompted in, not
    only the language the room reads: `text` and `text_it` are two prompts, and
    the model answers in the one it was given.
    """
    text = localized(beat, "text", language, default="")

    # `restates` is not `continues`. m5-p3's text begins "Same question." and
    # the deck's own tool field says *new conversation*: the beat's point is
    # that the discipline is in the prompt, not in the model having been
    # corrected. So the earlier beat's question is restated here, and no
    # transcript is carried — the model has never seen its own cold answer.
    # Prompt text is untouched (AGENTS.md rule 5): this composes two prompts
    # that both already exist in the database, it does not write a third.
    restates = block.get("restates")
    if restates:
        earlier = find_beat(restates["demo"], restates["beat"], sector)
        text = f"{localized(earlier, 'text', language, default='')}\n\n{text}"

    for spec in block.get("inputs", []):
        paste_file = spec.get("paste_file")
        if not paste_file:
            continue
        content = read_input_file(paste_file, sector)

        # The placeholder is part of the prompt, so it is written in the
        # prompt's language: the deck says "[PASTE RAW NOTES]" in English and
        # "[INCOLLA APPUNTI GREZZI]" in Italian. Substituting the English one
        # into an Italian prompt silently sends the model the literal
        # placeholder instead of the pasted file.
        placeholder = localized(spec, "replaces", language)
        if placeholder:
            text = text.replace(placeholder, content)
            continue

        # No placeholder. Several beats name a `paste_file` in the demo
        # database and have no hole for it — D2's two beats both say "these
        # four drafts" and expect the drafts to be in the conversation already,
        # because in the room a person pastes them under the question. There is
        # nothing to substitute, so the material is appended, which is the same
        # thing that person does. Prompt text is untouched (AGENTS.md rule 5):
        # this is about where the file goes, not about what the prompt says.
        if spec.get("append"):
            text = f"{text.rstrip()}\n\n{content.strip()}"

    return text


def plan(
    demo_id: str,
    beat_id: str,
    sector: str,
    sources: dict[str, ModelSource],
    *,
    language: str = DEFAULT_LANGUAGE,
) -> RunPlan:
    """Assemble a complete, executable plan for one beat.

    Raises
    ------
    KeyError
        If the beat does not exist in the demo database.
    LookupError
        If the beat exists but has no run block. The message carries the reason
        recorded in run-blocks.json, so "why can I not run this" is answerable
        from the stage console without reading the source.
    """
    beat = find_beat(demo_id, beat_id, sector)
    block = run_block(beat_id)
    if block is None:
        reason = unblocked_reason(beat_id, language) or t("runs.no_run_block", language)
        raise LookupError(
            t("runs.not_executable", language, beat_id=beat_id, reason=reason)
        )

    # The prompt is built first because it is also the retrieval query: rung 3
    # must search for the question the room is about to watch being asked, not
    # for a paraphrase of it kept somewhere else.
    prompt = build_prompt(beat, block, sector, language=language)
    panes = bind_panes(block, sources, lang=language, sector=sector, query=prompt)
    required = int(block.get("requires_sources", 1))
    # Distinct *(provider, model)* pairs, not distinct providers. Two panes on
    # one provider at two model sizes are two sources for every purpose a beat
    # cares about — that is precisely D2's configuration, a small judge against
    # a large one, and counting providers would have marked it degraded and
    # announced a replay that was not needed. It is also the right measure for
    # D1, whose own note says the beat teaches that "two models disagree with
    # each other".
    distinct_bound = len({(p.source.provider, p.source.model) for p in panes if p.source})

    return RunPlan(
        beat_id=beat_id,
        demo_id=demo_id,
        sector=sector,
        prompt=prompt,
        panes=panes,
        continues=block.get("continues"),
        produces=block.get("produces"),
        teaches=localized(block, "teaches", language),
        inputs=tuple(block.get("inputs", [])),
        teaches_params=tuple(block.get("teaches_params", [])),
        language_mismatches=language_mismatches(block, sector, language),
        degraded=distinct_bound < required or any(not p.runnable for p in panes),
        language=language,
    )

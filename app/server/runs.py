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

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

from app.server.demos import DB_PATH, data_root, resolve_demo

RUN_BLOCKS_PATH = DB_PATH.parent / "run-blocks.json"

Role = Literal["primary", "secondary", "local"]

#: Why a pane could not be bound. Carried to the harness so the room is told
#: what is replayed and why, rather than shown a silently shorter demo.
UNAVAILABLE_NO_SOURCE = "no model source configured for this role"


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
    temperature_applies: bool = True


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
    degraded: bool = False

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
        raise FileNotFoundError(
            f"Run blocks missing at {RUN_BLOCKS_PATH}. Banco cannot execute any "
            "beat without them; see docs/adr/0003."
        )
    import json

    return json.loads(RUN_BLOCKS_PATH.read_text(encoding="utf-8"))


def run_block(beat_id: str) -> dict | None:
    """The run block for `beat_id`, or None if the beat is not executable.

    None is a legitimate answer: library and archived beats deliberately have
    none, and the `_unblocked` map in the file records why for each.
    """
    return load_run_blocks().get("beats", {}).get(beat_id)


def unblocked_reason(beat_id: str) -> str | None:
    """Why a beat has no run block, if the file says."""
    return load_run_blocks().get("_unblocked", {}).get(beat_id)


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


def bind_panes(block: dict, sources: dict[str, ModelSource]) -> tuple[Pane, ...]:
    """Bind each pane's role to a configured source, or mark it unavailable.

    `sources` maps role -> ModelSource and comes from the profile chosen at
    first run. A role with no source yields an unavailable pane carrying the
    reason; the caller degrades the beat rather than dropping the pane, so the
    room still sees four panes and is told which are replayed.
    """
    panes: list[Pane] = []
    for index, spec in enumerate(block.get("panes", [])):
        role = spec.get("role", "primary")
        source = sources.get(role)
        panes.append(
            Pane(
                pane=spec.get("pane", index),
                label=spec.get("label", f"pane {index}"),
                role=role,
                temperature=float(spec.get("temperature", 0.3)),
                thinking=spec.get("thinking"),
                source=source,
                unavailable=None if source else UNAVAILABLE_NO_SOURCE,
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
        raise ValueError(
            f"Input path escapes the sector demo directory: {relative_path!r}"
        )
    if not target.is_file():
        raise FileNotFoundError(f"Input file missing: {target}")
    return target.read_text(encoding="utf-8")


def build_prompt(beat: dict, block: dict, sector: str, *, language: str = "en") -> str:
    """The prompt as it will be sent, with pasted files substituted in.

    Returns the text the room is entitled to see on screen: objective 2 says
    the system prompt *as sent* is visible, and that has to include whatever a
    paste placeholder expanded to.
    """
    key = "text_it" if language == "it" else "text"
    text = beat.get(key) or beat.get("text") or ""

    for spec in block.get("inputs", []):
        paste_file = spec.get("paste_file")
        placeholder = spec.get("replaces")
        if not paste_file or not placeholder:
            continue
        text = text.replace(placeholder, read_input_file(paste_file, sector))

    return text


def plan(
    demo_id: str,
    beat_id: str,
    sector: str,
    sources: dict[str, ModelSource],
    *,
    language: str = "en",
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
        reason = unblocked_reason(beat_id) or "no run block defined"
        raise LookupError(f"{beat_id} is not executable: {reason}")

    panes = bind_panes(block, sources)
    required = int(block.get("requires_sources", 1))
    distinct_bound = len({p.source.provider for p in panes if p.source})

    return RunPlan(
        beat_id=beat_id,
        demo_id=demo_id,
        sector=sector,
        prompt=build_prompt(beat, block, sector, language=language),
        panes=panes,
        continues=block.get("continues"),
        produces=block.get("produces"),
        teaches=block.get("teaches"),
        inputs=tuple(block.get("inputs", [])),
        degraded=distinct_bound < required or any(not p.runnable for p in panes),
    )

"""Execute one beat across its panes and stream what happens.

The provider interface is synchronous and `generate_stream` yields text chunks,
so each pane runs in its own thread and pushes events onto one queue, which is
drained in order of arrival. No provider needed rewriting for this, and the
panes genuinely run at the same time - which matters, because a room watching
four panes fill one after another learns something false about how this works.

Every event that reaches the harness carries the pane it belongs to and the
mechanism the room is entitled to see: provider, model, temperature, thinking
budget, token counts, and where the request went.

Nothing here fabricates output. A pane with no source emits `pane_unavailable`
and renders as unavailable; it never emits text (AGENTS.md rule 1).
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from collections.abc import Iterator
from datetime import datetime, timezone

from app.i18n import t
from app.llm.base import LLMError, LLMMessage
from app.llm.router import LLMRouter
from app.server.demos import data_root
from app.server.runs import Pane, RunPlan
from app.utils.redact import redact, secret_values

logger = logging.getLogger("raggy.runner")

#: Conversation history per pane, so a beat marked `continues` can interrogate
#: what that same pane produced. Process-local and deliberately not persisted:
#: Banco is one trainer on one machine, and a transcript surviving a restart
#: would let a beat interrogate an answer from a previous lesson.
_TRANSCRIPTS: dict[tuple[str, str, int], list[LLMMessage]] = {}

_SENTINEL = object()


def transcript_key(sector: str, beat_id: str, pane: int) -> tuple[str, str, int]:
    return (sector, beat_id, pane)


def reset_transcripts() -> None:
    """Forget every stored exchange. Called between dry runs and by tests."""
    _TRANSCRIPTS.clear()


def sse(event: str, data: dict) -> str:
    """One Server-Sent Event. `data` is JSON on a single line."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _pane_payload(pane: Pane, prepared=None, lang: str | None = None) -> dict:
    """A pane as the harness receives it. Mechanism visible, nothing else.

    `sent` and `dropped` come from the request that was actually built, not
    from a capability table, and they ride the `plan` event because the harness
    lays out its panes before any text arrives and has to be able to label them
    truthfully at that moment.

    A `dropped` reason is prose on a projected surface, so it is translated
    here, in the language the run was planned in (AGENTS.md rule 9).
    """
    payload = {
        "pane": pane.pane,
        "label": pane.label,
        "role": pane.role,
        "temperature": pane.temperature,
        "thinking": pane.thinking,
        "unavailable": pane.unavailable,
        "sent": {},
        "dropped": {},
    }
    if pane.source is not None:
        payload |= {
            "provider": pane.source.provider,
            "model": pane.source.model,
            "egress": pane.source.egress,
            "local": pane.source.local,
            "temperature_applies": pane.source.temperature_applies,
        }
    if prepared is not None:
        # `sent` is redacted before it leaves the process. It is built from a
        # payload that was constructed beside a credential, and this dict is
        # rendered on the projected surface (PROJECT.md invariant 1).
        payload["sent"] = {k: redact(v) if isinstance(v, str) else v
                           for k, v in prepared.sent.items()}
        payload["dropped"] = {
            name: t(reason, lang) for name, reason in prepared.dropped.items()
        }
        # Derived from the same source of truth rather than asked of a second
        # one, so the two can never disagree on a screen.
        payload["temperature_applies"] = "temperature" not in prepared.dropped
    return payload


def _messages_for(plan: RunPlan, pane: Pane) -> list[LLMMessage]:
    """The conversation as sent, including any earlier beat this one continues.

    `continues` is not cosmetic: m1-p2 asks the model where a value in *its own*
    previous answer came from. Sending that question without the prior exchange
    would ask about nothing, and the beat would teach nothing.
    """
    history: list[LLMMessage] = []
    if plan.continues:
        history = list(
            _TRANSCRIPTS.get(transcript_key(plan.sector, plan.continues, pane.pane), [])
        )
    return [*history, LLMMessage(role="user", content=plan.prompt)]


def _prepare_pane(plan: RunPlan, pane: Pane, max_tokens: int, credentials: dict[str, dict]):
    """The request this pane will send, built before the run starts.

    Returns None when the request cannot even be built — a missing key, an SDK
    that will not import. That is not smoothed over: the pane still runs, fails
    for the same reason, and is narrated as a failure. What is lost is only the
    parameter strip, and a pane showing no parameter makes no claim about one.
    """
    if pane.source is None:
        return None
    try:
        router = LLMRouter(
            pane.source.provider,
            model=pane.source.model,
            temperature=pane.temperature,
            max_tokens=max_tokens,
            **credentials.get(pane.source.provider, {}),
        )
        return router.prepare(_messages_for(plan, pane), pane.params, model=pane.source.model)
    except Exception:  # noqa: BLE001 - reported by the run itself, moments later
        logger.debug("Could not prepare pane %s in advance", pane.pane, exc_info=True)
        return None


def _run_pane(
    plan: RunPlan,
    pane: Pane,
    events: queue.Queue,
    max_tokens: int,
    credentials: dict[str, dict],
) -> None:
    """Stream one pane into the queue. Runs on its own thread.

    `credentials` maps provider name to constructor arguments. It is passed in
    rather than read here so that this module never touches configuration, and
    so a key has exactly one path into the process.
    """
    messages = _messages_for(plan, pane)
    chunks: list[str] = []

    # A provider's own error text is not trusted to be credential-free. Google
    # sends the key as a URL query parameter and OpenAI echoes the key it
    # rejected, so `str(exc)` can carry one, and the event built below is
    # rendered on the projected surface. PROJECT.md invariant 1.
    kwargs = credentials.get(pane.source.provider, {})
    secrets = secret_values(kwargs)

    try:
        router = LLMRouter(
            pane.source.provider,
            model=pane.source.model,
            temperature=pane.temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        # Built once, here, and sent. The same object was prepared before the
        # stream opened so the harness could label the pane; preparing again
        # rather than passing that one across a thread boundary keeps this
        # function's only input the pane, and `prepare` is pure.
        request = router.prepare(messages, pane.params, model=pane.source.model)
        for chunk in router.generate_stream(messages, request=request):
            chunks.append(chunk)
            events.put(("delta", {"pane": pane.pane, "text": chunk}))
    except LLMError as exc:
        # A provider failure is narrated, never smoothed over: the room is
        # entitled to see that this pane did not answer, and why. Redacted, so
        # that "why" never turns out to include the key.
        events.put(
            (
                "pane_failed",
                {
                    "pane": pane.pane,
                    "error": redact(f"{type(exc).__name__}: {exc}", *secrets),
                },
            )
        )
        return
    except Exception as exc:  # noqa: BLE001 - one pane must not kill the run
        logger.exception("Pane %s crashed", pane.pane)
        events.put(
            (
                "pane_failed",
                {
                    "pane": pane.pane,
                    "error": redact(f"{type(exc).__name__}: {exc}", *secrets),
                },
            )
        )
        return

    text = "".join(chunks)
    _TRANSCRIPTS[transcript_key(plan.sector, plan.beat_id, pane.pane)] = [
        *messages,
        LLMMessage(role="assistant", content=text),
    ]
    events.put(
        (
            "pane_done",
            {
                "pane": pane.pane,
                "characters": len(text),
                "egress": pane.source.egress,
                "local": pane.source.local,
            },
        )
    )


def write_chain_file(plan: RunPlan, outputs: dict[int, str]) -> str | None:
    """Overwrite the handover file this beat produces, on full success only.

    Invariant 3: the chain never waits. The file already exists before the
    lesson; a successful run overwrites it, and a failed one leaves it intact so
    the trainer can open the shipped version and carry on. That is why this is
    called only when every pane produced text.

    The header records which source and temperature produced each draft, because
    the next demo judges these drafts and "which model wrote this" is part of
    what is being judged.
    """
    if not plan.produces:
        return None

    target = (data_root(plan.sector) / plan.produces).resolve()
    root = data_root(plan.sector).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"produces path escapes the sector directory: {plan.produces!r}")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    # In the language the beat ran in: the next demo reads this file in front of
    # the room, and a Italian lesson must not hand it an English header.
    lines = [
        # Machine-readable, and first. The header below says the language in
        # prose; this says it to `runs.chain_file_language`, which is what lets
        # a later beat notice that the material it is about to paste into an
        # Italian prompt was written in English by an earlier run.
        f"<!-- banco:lang={plan.language} -->",
        "<!-- " + t("chain.written_by", plan.language, beat_id=plan.beat_id, stamp=stamp) + " -->",
        "<!-- " + t("chain.overwritten", plan.language, sector=plan.sector) + " -->",
        "",
    ]
    for pane in plan.panes:
        text = outputs.get(pane.pane)
        if text is None or pane.source is None:
            continue
        lines += [
            f"## {pane.label}",
            "",
            "`" + t("chain.produced_by", plan.language, provider=pane.source.provider,
                    model=pane.source.model, temperature=pane.temperature) + "`",
            "",
            text.strip(),
            "",
        ]

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return plan.produces


def stream_beat(
    plan: RunPlan,
    *,
    max_tokens: int = 1500,
    credentials: dict[str, dict] | None = None,
) -> Iterator[str]:
    """Run every runnable pane concurrently and yield SSE text.

    Event order is arrival order, except that `plan` is always first and
    `run_done` always last, so the harness can lay out its panes before any
    text arrives and knows when to stop listening.
    """
    prepared = {
        p.pane: _prepare_pane(plan, p, max_tokens, credentials or {})
        for p in plan.panes
    }

    yield sse(
        "plan",
        {
            "demo_id": plan.demo_id,
            "beat_id": plan.beat_id,
            "sector": plan.sector,
            "teaches": plan.teaches,
            "teaches_params": list(plan.teaches_params),
            "language_mismatches": list(plan.language_mismatches),
            "prompt": plan.prompt,
            "continues": plan.continues,
            "produces": plan.produces,
            "degraded": plan.degraded,
            "replayed": False,
            "panes": [
                _pane_payload(p, prepared.get(p.pane), plan.language) for p in plan.panes
            ],
        },
    )

    for pane in plan.panes:
        if not pane.runnable:
            # Announced, never quietly skipped, and never filled with invented
            # text. There is no recording yet (M3), so the pane says so.
            yield sse(
                "pane_unavailable",
                {
                    "pane": pane.pane,
                    "reason": pane.unavailable,
                    "would_replay": True,
                    "recording": None,
                },
            )

    runnable = plan.runnable_panes
    if not runnable:
        yield sse("run_done", {"beat_id": plan.beat_id, "produced": None, "ran": 0})
        return

    events: queue.Queue = queue.Queue()
    threads = [
        threading.Thread(
            target=_run_pane,
            args=(plan, pane, events, max_tokens, credentials or {}),
            name=f"banco-pane-{pane.pane}",
            daemon=True,
        )
        for pane in runnable
    ]
    for thread in threads:
        thread.start()

    def _watch() -> None:
        for thread in threads:
            thread.join()
        events.put(_SENTINEL)

    threading.Thread(target=_watch, name="banco-watch", daemon=True).start()

    collected: dict[int, list[str]] = {p.pane: [] for p in runnable}
    failed: set[int] = set()

    while True:
        item = events.get()
        if item is _SENTINEL:
            break
        name, payload = item
        if name == "delta":
            collected[payload["pane"]].append(payload["text"])
        elif name == "pane_failed":
            failed.add(payload["pane"])
        yield sse(name, payload)

    produced = None
    every_pane_succeeded = not failed and len(runnable) == len(plan.panes)
    if every_pane_succeeded:
        outputs = {pane: "".join(parts) for pane, parts in collected.items()}
        try:
            produced = write_chain_file(plan, outputs)
        except OSError as exc:
            yield sse("chain_failed", {"error": redact(exc), "file": plan.produces})

    yield sse(
        "run_done",
        {
            "beat_id": plan.beat_id,
            "produced": produced,
            "ran": len(runnable),
            "failed": sorted(failed),
            "chain_held": bool(plan.produces) and produced is None,
        },
    )

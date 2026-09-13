"""Pre-flight: everything a trainer must know before a lesson starts.

This is the answer to "am I ready", asked on the stage console and never on the
projected surface. It reports *presence*, never a credential: a key is `true` or
`false` here and nothing else, not a masked fragment and not a last-four - a
fragment on a screen that has been projected by accident is still a fragment of
a real key.

Every check is a plain function so it can be run from a test, from the console,
and eventually from an agent completing installation unattended (objective 6).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

from app.i18n import localized, normalize, t
from app.server import demos, sessions, sources
from app.utils.redact import redact, secret_values

logger = logging.getLogger("raggy.preflight")

#: Placeholder shipped in `.env.example`. Treated as "no password set", because
#: it is the value every fresh install has and none of them chose.
DEFAULT_ADMIN_PASSWORD = "changeme"  # noqa: S105 - a placeholder to reject, not a secret

#: The handover files that must exist before a lesson (PROJECT.md invariant 3).
CHAIN_FILES = (
    "demo/catena/d1-bozze.md",
    "demo/catena/d2-criteri.md",
    "demo/catena/d3-fonte.md",
    "demo/catena/d4-tabella.md",
    "demo/catena/d5-verifiche-umane.md",
)


@dataclass(frozen=True, slots=True)
class Check:
    """One pre-flight line: what it is, whether it passes, and what to do."""

    ok: bool
    detail: str
    action: str | None = None


def admin_password(settings, *, lang: str | None = None) -> Check:
    """Whether the console is protected by a password the trainer chose."""
    value = (getattr(settings, "admin_password", "") or "").strip()
    if not value or value == DEFAULT_ADMIN_PASSWORD:
        return Check(
            ok=False,
            detail=t("preflight.password.missing", lang),
            action=t("preflight.password.missing.action", lang),
        )
    return Check(ok=True, detail=t("preflight.password.ok", lang))


def api_keys(settings) -> dict[str, bool]:
    """Which API providers have a key. Presence only - never the value."""
    return {
        provider: bool(sources._api_key_for(provider, settings))
        for provider in sources.API_ORDER
    }


def ollama(settings, *, probe: bool = True) -> dict[str, Any]:
    """Whether Ollama is installed, running, and which models are present.

    `probe` exists so the console can render immediately and fill this in
    afterwards: `is_ollama_running` waits on a socket, and a trainer opening the
    console should not watch a blank page while it does.
    """
    from app.llm.ollama_setup import (
        get_system_info,
        is_ollama_installed,
        is_ollama_running,
        recommend_models,
    )

    base_url = settings.ollama_base_url
    installed = is_ollama_installed()
    running = is_ollama_running(base_url) if (probe and installed) else False

    models: list[str] = []
    if running:
        try:
            from app.llm.providers.ollama import OllamaProvider

            models = OllamaProvider(base_url=base_url).available_models()
        except Exception as exc:  # noqa: BLE001 - reported, never raised at a trainer
            models = []
            return {
                "installed": installed,
                "running": running,
                "base_url": base_url,
                "models": models,
                "error": redact(f"{type(exc).__name__}: {exc}"),
                "system": {},
                "recommended": [],
            }

    system = get_system_info() if installed else {}
    return {
        "installed": installed,
        "running": running,
        "base_url": base_url,
        "models": models,
        "system": system,
        "recommended": recommend_models(system) if system else [],
    }


def _models_hint(router, source=None, settings=None, lang: str | None = None) -> str:
    """What this provider will actually accept, appended to a 404.

    Model ids rot, and they rot between lessons: `gemini-2.5-flash` started
    answering "no longer available to new users" and `gemma3:4b` was simply not
    pulled on this machine. "Not found" on its own sends a trainer to a search
    engine minutes before a lesson; the live list answers it in one call.

    **The provenance is part of the answer.** This used to print up to eight
    ids with nothing to say whether they came from the provider's API or from
    `model_catalog.FALLBACK_MODELS`, a static list last verified in June 2026.
    A trainer reading a stale static list as an API answer picks a model the
    API will refuse — and does it while fixing the error that produced the
    hint. `model_catalog` has always known which it was; nothing surfaced it.

    Silent on failure — this is a garnish on an error that is already reported,
    and a second failure must not replace the first one's message.
    """
    try:
        models = router.available_models()
    except Exception:  # noqa: BLE001 - a hint that cannot be fetched is just absent
        return ""
    if not models:
        return ""

    live = _list_is_live(router, source, settings)
    shown = ", ".join(models[:8]) + ("…" if len(models) > 8 else "")
    key = "preflight.source.models_hint" if live else "preflight.source.models_hint_fallback"
    return " " + t(key, lang, models=shown)


def _list_is_live(router, source, settings) -> bool:
    """Whether the list just returned came from the provider, not the backstop.

    Ollama is always live: its list is `/api/tags` on this machine, which has no
    static fallback to be confused with.
    """
    provider = getattr(source, "provider", None) or getattr(router, "provider_name", "")
    if provider == "ollama":
        return True
    from app.llm.providers import model_catalog

    key = None
    if settings is not None:
        credential = sources._api_key_for(provider, settings)
        if credential:
            key = model_catalog.credential_cache_key(credential)
    return model_catalog.is_live(provider, cache_key=key)


def _stored_but_failing(provider: str, lang: str | None = None) -> str:
    """The next step, which is not the same one for every provider.

    Ollama has no key, so "the key is stored but not working" sent a trainer to
    look for a credential that does not exist.
    """
    if provider == "ollama":
        return t("preflight.source.ollama_no_model", lang)
    return t("preflight.source.key_stored_call_failed", lang)


def check_source(role: str, source, settings, *, lang: str | None = None) -> Check:
    """Actually call the provider and see whether it answers.

    Everything else in pre-flight reports configuration: a key is present, a
    port is open. This is the only check that answers the question a trainer
    actually has, which is whether the key *works* - a rotated key, a spent
    quota and an expired card all look identical until something is sent.

    It costs a real call, so it is never run on page load. The console asks for
    it explicitly.
    """
    from app.llm.base import LLMError, LLMMessage, LLMModelNotFoundError
    from app.llm.router import LLMRouter

    router = None

    # The key used for this call, so the failure text below can be scrubbed of
    # it. A provider's own message is not trusted to be credential-free, and
    # this detail is rendered on the console and written to the log.
    kwargs = sources.provider_kwargs(source.provider, settings)
    secrets = secret_values(kwargs)

    try:
        router = LLMRouter(source.provider, model=source.model, **kwargs)
        # `router.test_connection()` is deliberately NOT used. Every provider's
        # implementation catches all exceptions and returns False, so the whole
        # reason — wrong key, retired model, no network, budget spent — is
        # discarded inside the provider, and this check could only ever say
        # "did not answer". That is the one thing a trainer cannot act on, and
        # it is the only check that exists to distinguish a working key from a
        # stored one. Calling `generate` directly keeps the exception.
        router.generate([LLMMessage(role="user", content="ping")], max_tokens=16)
        return Check(
            ok=True,
            detail=t("preflight.source.ok", lang, role=role,
                     provider=source.provider, model=source.model),
        )
    except LLMModelNotFoundError as exc:
        # Handled before LLMError, which it subclasses: a retired or unpulled
        # model is the one failure where naming the alternatives fixes it.
        return Check(
            ok=False,
            detail=t("preflight.source.refused", lang, role=role, provider=source.provider,
                     error=redact(f"{type(exc).__name__}: {exc}", *secrets))
                   + _models_hint(router, source, settings, lang),
            action=_stored_but_failing(source.provider, lang),
        )
    except LLMError as exc:
        # The provider's own message is inserted, never translated: it is
        # evidence, and a rewritten error is no longer what the provider said.
        return Check(
            ok=False,
            detail=t("preflight.source.refused", lang, role=role, provider=source.provider,
                     error=redact(f"{type(exc).__name__}: {exc}", *secrets)),
            action=_stored_but_failing(source.provider, lang),
        )
    except Exception as exc:  # noqa: BLE001 - reported to a trainer, never raised
        return Check(
            ok=False,
            detail=t("preflight.source.failed", lang, role=role, provider=source.provider,
                     error=redact(f"{type(exc).__name__}: {exc}", *secrets)),
        )


def live_checks(settings, *, lang: str | None = None) -> dict[str, dict[str, Any]]:
    """Call every *configured* source once. The slow, honest part of pre-flight.

    Configured, not merely bound. There are two API roles and there can be
    three keys, so binding leaves one provider filling no pane — and with
    Anthropic, OpenAI and Google all set, Google was silently absent from the
    one check that tells a working key from a stored one. A key nobody reports
    on is a key discovered to be wrong in the room.

    Bound sources keep their role as the key so the report still reads
    `primary` / `secondary` / `local`; a configured provider with no pane is
    keyed by its own name.
    """
    bound = sources.available_sources(settings)
    checks = {
        role: asdict(check_source(role, source, settings, lang=lang))
        for role, source in sorted(bound.items())
    }

    bound_providers = {source.provider for source in bound.values()}
    for provider in sources.configured_api_providers(settings):
        if provider in bound_providers:
            continue
        checks[provider] = asdict(
            check_source(
                t("preflight.source.no_pane", lang, provider=provider),
                sources.api_source(provider),
                settings,
                lang=lang,
            )
        )

    return checks


def _would_carry(
    provider: str, model: str, params: dict, parameter: str
) -> tuple[bool, str | None]:
    """Whether this (provider, model) would actually send `parameter`.

    Answered by building the request, not by consulting a table: `prepare` is
    pure and touches no client, so the same code that decides what reaches the
    API decides what pre-flight promises about it. A table would be a second
    source of truth able to disagree with the first.

    Only `parameter` is judged. A source that carries the budget this beat
    teaches but drops a temperature nobody asked about is still the right
    source for this beat, and the temperature has its own warning.

    Returns `(carried, reason)`, where `reason` is the i18n key `prepare`
    recorded — never the parameter's own name, which is what a first version of
    this function returned and would have rendered as a reason saying "think".
    """
    from app.llm.base import LLMMessage
    from app.llm.router import _load_provider_class

    try:
        provider_class = _load_provider_class(provider)
        prepared = provider_class.for_inspection(model).prepare(
            [LLMMessage(role="user", content="")], params
        )
    except Exception:  # noqa: BLE001 - an unanswerable check is not a claim
        logger.debug("Could not inspect %s/%s", provider, model, exc_info=True)
        return False, None
    if parameter in prepared.dropped:
        return False, prepared.dropped[parameter]
    return parameter in prepared.sent, None


def capability_warnings(
    settings, *, check_ollama: bool = True, lang: str | None = None
) -> list[dict]:
    """Per demo: will the parameters it teaches actually be sent?

    A demo whose only temperature knob is bound to a model that discards
    temperature runs, looks correct on a projector and teaches nothing. This is
    the check that catches it before the room does — the pre-flight equivalent
    of `temperature_is_applied`, generalised to every parameter a beat declares.

    Advisory, never a hard failure: a trainer may knowingly rehearse a demo on a
    model that ignores the knob. What it must not do is stay silent, and what it
    must always carry is the fix — which configured source *would* apply the
    parameter, so the change is one select away.

    Free and offline. `prepare` makes no call, so this can run on page load for
    every demo. `POST /console/check` is the slower, authoritative version that
    sends the parameter and reads `dropped` back from a real request.
    """
    from app.server import sessions
    from app.server.runs import load_run_blocks, pane_params

    blocks = load_run_blocks().get("beats", {})
    warnings: list[dict] = []

    by_demo: dict[str, list[tuple[str, dict]]] = {}
    for beat_id, block in blocks.items():
        if block.get("teaches_params"):
            by_demo.setdefault(beat_id.split("-", 1)[0], []).append((beat_id, block))

    for demo_id, beats in sorted(by_demo.items()):
        bound = sessions.resolve(settings, demo_id, check_ollama=check_ollama)
        for beat_id, block in beats:
            for parameter in block.get("teaches_params", []):
                asks = _panes_asking(block, parameter)
                if not asks:
                    continue

                # Carried if at least one *bound* pane sends it. One is enough:
                # D2's "off" pane and "on" pane are a pair, and a source that
                # carries the budget carries both halves of the comparison.
                carried = False
                reason: str | None = None
                for pane in asks:
                    source = bound.get(pane.get("role", "primary"))
                    if source is None:
                        continue
                    ok, why = _would_carry(
                        source.provider, source.model,
                        pane_params(pane, source), parameter,
                    )
                    carried = carried or ok
                    reason = reason or why
                if carried:
                    continue

                alternatives = _alternatives(settings, asks, parameter,
                                             check_ollama=check_ollama)
                warnings.append({
                    "demo": demo_id,
                    "beat": beat_id,
                    "parameter": parameter,
                    "reason": t(reason, lang) if reason else None,
                    "detail": t("preflight.capability.not_carried", lang,
                                demo=demo_id, beat=beat_id, parameter=parameter),
                    "alternatives": alternatives,
                    "action": (
                        t("preflight.capability.alternatives", lang,
                          sources=", ".join(alternatives))
                        if alternatives
                        else t("preflight.capability.no_alternative", lang)
                    ),
                })
    return warnings


def _panes_asking(block: dict, parameter: str) -> list[dict]:
    """The panes of this beat that state `parameter` at all."""
    return [pane for pane in block.get("panes", []) if parameter in pane]


def _alternatives(settings, asks: list[dict], parameter: str, *, check_ollama: bool) -> list[str]:
    """Configured sources that *would* carry this parameter for this beat.

    A warning that only says what is broken costs a trainer the same search a
    bare "not found" does; naming the fix puts it one select away. Every source
    with a key on this machine is tried, whether or not it currently fills a
    pane — a configured provider bound to no role is exactly the one a trainer
    would move a role onto.

    A source qualifies only if it carries the parameter for **every** pane that
    asks for it. Anthropic takes D2's `think: 4096` and also its `think: false`;
    a source that took only one of the two would give the room half a
    comparison, which is worse than an honest warning.
    """
    from app.server.runs import pane_params

    candidates: list[tuple[str, str]] = [
        (provider, sources._default_model(provider))
        for provider in sources.configured_api_providers(settings)
    ]
    if check_ollama:
        local = sources.ollama_source(settings)
        if local is not None:
            candidates.append((local.provider, local.model))

    out: list[str] = []
    for provider, model in candidates:
        if all(
            _would_carry(provider, model, pane_params(pane, None), parameter)[0]
            for pane in asks
        ):
            out.append(f"{provider} · {model}")
    return out


#: The pseudo-path the demo database uses for "this sector's records folder".
#: `_files_note` in `demo-prompts.json` defines it; it is resolved here rather
#: than hard-coded, because the folder is `lotti` for numismatics and `schede`
#: for photovoltaic and nothing in the prompts knows which.
RECORDS_PSEUDO_PATH = "RECORDS/"


def _sector_record(sector: str) -> dict | None:
    """The sector's own block in the demo database, or None if undeclared."""
    return next(
        (s for s in demos.load().get("sectors", []) if s.get("id") == sector), None
    )


def _pack_command(folder: str) -> str:
    """The command that generates this sector's pack, as a trainer would run it.

    `--out` is part of it, not a detail: `generate.py` defaults to the kit's own
    output folder, and Banco reads `demo/data/<folder>`. A command that puts the
    pack somewhere Banco does not look is worse than no command at all, because
    it appears to have worked.
    """
    return f"python demo/kit/generate.py --settore {folder} --out demo/data/{folder}"


def _material_of(demo: dict, records_dir: str) -> list[dict]:
    """Every file this demo needs on disk, with the trainer-only ones marked.

    Two sources, because the database states the requirement in two places and
    a lesson needs both: `files[]` is the download rail on the slide, and
    `paste_file` is what the widget inlines into a prompt. A pack missing only
    the second one renders a complete slide and hands the room a prompt with a
    hole in it.

    `requires` is deliberately *not* read: it is a prose sentence about the room
    ("a calendar connector already connected"), not a path.
    """
    found: dict[str, dict] = {}

    def add(path: str | None, *, trainer: bool = False, label: str | None = None) -> None:
        if not path:
            return
        if path.startswith(RECORDS_PSEUDO_PATH):
            path = f"{records_dir}/" + path[len(RECORDS_PSEUDO_PATH):]
        entry = found.setdefault(path, {"path": path, "trainer": False, "label": label})
        # Marked trainer-only if *any* declaration says so: the flag keeps the
        # answer key off the projected rail, and the safe direction is to keep it off.
        entry["trainer"] = entry["trainer"] or bool(trainer)
        entry["label"] = entry["label"] or label

    for entry in demo.get("files") or []:
        if isinstance(entry, dict):
            add(entry.get("path"), trainer=bool(entry.get("trainer")), label=entry.get("label"))
    for prompt in demo.get("prompts") or []:
        if isinstance(prompt, dict):
            add(prompt.get("paste_file"))
    return list(found.values())


def _present(root, path: str) -> bool:
    """Whether one declared path is actually there.

    A trailing slash means a folder, and an empty folder counts as missing: D4's
    beat 7 is a task over the records folder and D5's is a task over the
    poisoned one, and both do nothing at all when the folder exists and holds
    nothing. That failure looks like the model declining to work.
    """
    target = root / path.rstrip("/")
    if path.endswith("/"):
        return target.is_dir() and any(target.iterdir())
    return target.is_file()


def demo_data(sector: str, *, lang: str | None = None) -> dict[str, Any]:
    """Which of this sector's demo material is on disk, demo by demo.

    Every demo the database declares, not only the ones Banco can execute today:
    a sector pack is complete or it is not, and the beats Banco cannot run yet
    are still performed in the room from the same folder.

    Reports, never raises. An unknown sector is a wrong selection on a console,
    which the console can show; an exception here would be a 500 on the screen a
    trainer opens to find out what is wrong.
    """
    record = _sector_record(sector)
    try:
        root = demos.data_root(sector)
    except KeyError:
        record = None
        root = None

    if record is None or root is None:
        return {
            "sector": sector,
            "unknown_sector": True,
            "ok": False,
            "root": None,
            "root_exists": False,
            "demos": {},
            "missing_demos": [],
        }

    records_dir = (record.get("data", {}) or {}).get("records_dir") or ""
    root_exists = root.is_dir()

    per_demo: dict[str, dict] = {}
    for demo in demos.load().get("demos", []):
        required = _material_of(demo, records_dir)
        # No folder means nothing in it: every declared path is reported missing
        # rather than the whole sector collapsing to one line, so the trainer
        # sees what a generated pack would contain.
        missing = (
            list(required)
            if not root_exists
            else [item for item in required if not _present(root, item["path"])]
        )
        per_demo[demo.get("id")] = {
            "ok": not missing,
            "title": localized(demo, "title", lang),
            "required": len(required),
            "missing": missing,
        }

    return {
        "sector": sector,
        "unknown_sector": False,
        "ok": root_exists and all(d["ok"] for d in per_demo.values()),
        "root": str(root),
        "root_exists": root_exists,
        "demos": per_demo,
        "missing_demos": sorted(d for d, s in per_demo.items() if not s["ok"]),
    }


def _material_check(state: dict, *, lang: str | None = None) -> Check:
    """One pre-flight line from an already-computed `demo_data` state."""
    if state["unknown_sector"]:
        return Check(
            ok=False,
            detail=t("preflight.material.unknown_sector", lang, sector=repr(state["sector"])),
        )

    record = _sector_record(state["sector"]) or {}
    folder = (record.get("data", {}) or {}).get("folder") or state["sector"]
    action = t("preflight.material.action", lang, command=_pack_command(folder))

    if not state["root_exists"]:
        return Check(
            ok=False,
            detail=t("preflight.material.no_pack", lang, root=state["root"]),
            action=action,
        )
    if state["ok"]:
        return Check(
            ok=True,
            detail=t("preflight.material.ok", lang, total=len(state["demos"])),
        )
    return Check(
        ok=False,
        detail=t("preflight.material.incomplete", lang,
                 count=len(state["missing_demos"]), total=len(state["demos"]),
                 names=", ".join(state["missing_demos"])),
        action=action,
    )


def demo_data_check(sector: str, *, lang: str | None = None) -> Check:
    """Whether this sector can run every demo, as one pre-flight line."""
    return _material_check(demo_data(sector, lang=lang), lang=lang)


def sectors_overview(*, lang: str | None = None) -> list[dict]:
    """Every declared sector, marked with whether its pack is on disk.

    A sector with no pack is listed and marked, never dropped from the picker:
    the trainer who needs to know it is missing is the one about to select it,
    and a sector that silently disappears reads as a database that lost it.
    """
    overview = []
    for sector in demos.sectors():
        state = demo_data(sector["id"], lang=lang)
        overview.append({
            "id": sector["id"],
            "label": localized(sector, "label", lang) or sector["id"],
            "folder": sector.get("folder"),
            "ready": state["ok"],
            "missing_demos": state["missing_demos"],
        })
    return overview


def deck() -> dict[str, Any]:
    """Which build of the theory-deck this demo database was vendored from.

    Shown on the console because the prompt text is *shared* with the deck
    (ADR 0001): a trainer whose slides disagree with what Banco sends is looking
    at two different commits, and nothing else on the screen would say so.
    """
    pin_file = demos.DB_PATH.parent / "DECK-PIN.txt"
    db = demos.load()
    return {
        "pin": pin_file.read_text(encoding="utf-8").strip() if pin_file.is_file() else None,
        "version": db.get("version"),
        "updated": db.get("updated"),
        "demos": len(db.get("demos", [])),
        "sectors": len(db.get("sectors", [])),
    }


def chain(sector: str, *, lang: str | None = None) -> Check:
    """Whether every handover file exists for this sector.

    Invariant 3: the chain never waits. A missing file is not a warning to note
    and move past - it means a demonstration has nothing to hand the next one
    when it fails, which is precisely when it is needed.
    """
    from app.server.demos import data_root

    try:
        root = data_root(sector)
    except KeyError:
        return Check(
            ok=False,
            detail=t("preflight.chain.unknown_sector", lang, sector=repr(sector)),
        )

    missing = [name for name in CHAIN_FILES if not (root / name).is_file()]
    if missing:
        return Check(
            ok=False,
            detail=t("preflight.chain.missing", lang, missing=len(missing),
                     total=len(CHAIN_FILES), names=", ".join(missing)),
            action=t("preflight.chain.missing.action", lang),
        )

    # Every file is present. The remaining question is what language it is in:
    # a rehearsal run in English overwrites the handover file, and the next
    # demo then pastes English material under an Italian prompt. The file is
    # there, so the chain has not stopped — but the room is about to read it.
    from app.server.runs import chain_file_language

    foreign = [
        name for name in CHAIN_FILES
        if (declared := chain_file_language(name, sector)) is not None
        and declared != normalize(lang)
    ]
    if foreign:
        return Check(
            ok=False,
            detail=t("preflight.chain.other_language", lang,
                     count=len(foreign), names=", ".join(foreign)),
            action=t("preflight.chain.other_language.action", lang),
        )
    return Check(ok=True, detail=t("preflight.chain.ok", lang, total=len(CHAIN_FILES)))


def recordings_present(*, lang: str | None = None) -> Check:
    """Whether any recording exists for replay.

    Not a failure yet: recordings arrive at M3. Reported so that "this beat will
    degrade to replay" is never followed in the room by the discovery that there
    is nothing to replay.
    """
    from app.server.demos import DB_PATH

    folder = DB_PATH.parent.parent / "recordings"
    found = sorted(p.name for p in folder.glob("*")) if folder.is_dir() else []
    if not found:
        return Check(
            ok=False,
            detail=t("preflight.recordings.none", lang),
            action=t("preflight.recordings.none.action", lang),
        )
    return Check(ok=True, detail=t("preflight.recordings.ok", lang, count=len(found)))


def report(
    settings,
    sector: str,
    *,
    probe_ollama: bool = True,
    lang: str | None = None,
) -> dict[str, Any]:
    """The whole pre-flight, as the console renders it.

    `lang` is the language of the *console browser* that asked, carried on the
    request. It is never read from process state: the console and the harness
    are routinely open at once and may be in different languages.
    """
    ollama_state = ollama(settings, probe=probe_ollama)
    keys = api_keys(settings)
    bound = sources.available_sources(settings, check_ollama=probe_ollama)
    profile = sources.profile_name(bound)

    password = admin_password(settings, lang=lang)
    chain_state = chain(sector, lang=lang)
    material = demo_data(sector, lang=lang)

    return {
        "profile": profile,
        "ready_to_run": profile != sources.PROFILE_NONE,
        "sector": sector,
        # The picker's own contents. The console cannot offer a sector it was
        # not told about, and a sector list that arrives empty is a picker a
        # trainer cannot use.
        "sectors": sectors_overview(lang=lang),
        "demo_data": material,
        "deck": deck(),
        "api_keys": keys,
        "ollama": ollama_state,
        "roles": {
            role: {"provider": s.provider, "model": s.model,
                   "egress": s.egress, "local": s.local}
            for role, s in sorted(bound.items())
        },
        "session_profile": sessions.active_name(settings),
        "profiles": sessions.list_profiles(settings, lang=lang),
        # Parameters a run block states that a profile also sets: not an error
        # and not a silent loss, so it is named here rather than discovered by
        # a trainer wondering why their setting had no effect
        # (docs/specs/model-control.md §2).
        "overridden_by_run_blocks": _overridden(settings),
        # Advisory and free — see `capability_warnings`. The authoritative
        # version costs a real call and lives behind POST /console/check.
        "capability_warnings": capability_warnings(
            settings, check_ollama=probe_ollama, lang=lang
        ),
        "checks": {
            # asdict, not __dict__: Check uses slots and has no instance dict.
            "demo_data": asdict(_material_check(material, lang=lang)),
            "admin_password": asdict(password),
            "chain": asdict(chain_state),
            "recordings": asdict(recordings_present(lang=lang)),
        },
        "unprotected": not password.ok,
    }


def _overridden(settings) -> dict[str, list[str]]:
    """Which profile parameters each demo's run blocks will win over."""
    name = sessions.active_name(settings)
    if name is None:
        return {}
    try:
        return sessions.overridden_by_run_blocks(sessions.load_profile(name))
    except (sessions.ProfileError, FileNotFoundError):
        # The profile's own failure is already reported in `profiles` above.
        return {}

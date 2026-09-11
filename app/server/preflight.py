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

from dataclasses import asdict, dataclass
from typing import Any

from app.server import sources

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


def admin_password(settings) -> Check:
    """Whether the console is protected by a password the trainer chose."""
    value = (getattr(settings, "admin_password", "") or "").strip()
    if not value or value == DEFAULT_ADMIN_PASSWORD:
        return Check(
            ok=False,
            detail="The stage console has no password. It is reachable by anything "
                   "running on this machine.",
            action="Set one below. Until then this console is open.",
        )
    return Check(ok=True, detail="Console password set.")


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
                "error": f"{type(exc).__name__}: {exc}",
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


def check_source(role: str, source, settings) -> Check:
    """Actually call the provider and see whether it answers.

    Everything else in pre-flight reports configuration: a key is present, a
    port is open. This is the only check that answers the question a trainer
    actually has, which is whether the key *works* - a rotated key, a spent
    quota and an expired card all look identical until something is sent.

    It costs a real call, so it is never run on page load. The console asks for
    it explicitly.
    """
    from app.llm.base import LLMError
    from app.llm.router import LLMRouter

    try:
        router = LLMRouter(
            source.provider,
            model=source.model,
            **sources.provider_kwargs(source.provider, settings),
        )
        if router.test_connection():
            return Check(ok=True, detail=f"{role}: {source.provider} answered as {source.model}.")
        return Check(
            ok=False,
            detail=f"{role}: {source.provider} did not answer.",
            action="Check the key and the network, then run the check again.",
        )
    except LLMError as exc:
        return Check(
            ok=False,
            detail=f"{role}: {source.provider} refused - {type(exc).__name__}: {exc}",
            action="The key is stored but not working.",
        )
    except Exception as exc:  # noqa: BLE001 - reported to a trainer, never raised
        return Check(
            ok=False,
            detail=f"{role}: {source.provider} failed - {type(exc).__name__}: {exc}",
        )


def live_checks(settings) -> dict[str, dict[str, Any]]:
    """Call every configured source once. The slow, honest part of pre-flight."""
    bound = sources.available_sources(settings)
    if not bound:
        return {}
    return {
        role: asdict(check_source(role, source, settings))
        for role, source in sorted(bound.items())
    }


def chain(sector: str) -> Check:
    """Whether every handover file exists for this sector.

    Invariant 3: the chain never waits. A missing file is not a warning to note
    and move past - it means a demonstration has nothing to hand the next one
    when it fails, which is precisely when it is needed.
    """
    from app.server.demos import data_root

    try:
        root = data_root(sector)
    except KeyError:
        return Check(ok=False, detail=f"Unknown sector {sector!r}.")

    missing = [name for name in CHAIN_FILES if not (root / name).is_file()]
    if missing:
        return Check(
            ok=False,
            detail=f"{len(missing)} of {len(CHAIN_FILES)} handover files missing: "
                   + ", ".join(missing),
            action="Regenerate them with demo/kit/generate_chain.py before the lesson.",
        )
    return Check(ok=True, detail=f"All {len(CHAIN_FILES)} handover files present.")


def recordings_present() -> Check:
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
            detail="No recordings. A degraded pane will show its reason and no output.",
            action="Capture during the dry run once M3 lands.",
        )
    return Check(ok=True, detail=f"{len(found)} recordings on disk.")


def report(settings, sector: str, *, probe_ollama: bool = True) -> dict[str, Any]:
    """The whole pre-flight, as the console renders it."""
    ollama_state = ollama(settings, probe=probe_ollama)
    keys = api_keys(settings)
    bound = sources.available_sources(settings, check_ollama=probe_ollama)
    profile = sources.profile_name(bound)

    password = admin_password(settings)
    chain_state = chain(sector)

    return {
        "profile": profile,
        "ready_to_run": profile != sources.PROFILE_NONE,
        "sector": sector,
        "api_keys": keys,
        "ollama": ollama_state,
        "roles": {
            role: {"provider": s.provider, "model": s.model,
                   "egress": s.egress, "local": s.local}
            for role, s in sorted(bound.items())
        },
        "checks": {
            # asdict, not __dict__: Check uses slots and has no instance dict.
            "admin_password": asdict(password),
            "chain": asdict(chain_state),
            "recordings": asdict(recordings_present()),
        },
        "unprotected": not password.ok,
    }

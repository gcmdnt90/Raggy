"""Bind the configured profile to pane roles, and name every egress target.

A run block asks for a role (`primary`, `secondary`, `local`); this module is
the only place that decides which concrete provider answers. Keeping that
decision here is what lets the same run block run under `classroom` and under
`offline`, degrading instead of breaking (PROJECT.md, Configuration model).

It also owns the egress target for each source. Invariant 4 says every call
shows its destination, so the destination must be known before the call is made
and must come from one table rather than from each provider's internals.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from app.server.runs import ModelSource

#: Where a call to each API provider actually goes. Hard-coded deliberately:
#: the room is shown this string, so it must be true even if an SDK changes its
#: internal base URL, and a wrong value here is a teaching error, not a bug.
API_EGRESS = {
    "anthropic": "api.anthropic.com",
    "openai": "api.openai.com",
    "google": "generativelanguage.googleapis.com",
}

#: The order in which configured API providers fill `primary` then `secondary`.
#: Stable so that two runs of the same beat put the same provider in the same
#: pane: the room is comparing panes, and panes that move mean nothing.
API_ORDER = ("anthropic", "openai", "google")

PROFILE_CLASSROOM = "classroom"
PROFILE_TAKE_HOME = "take-home"
PROFILE_OFFLINE = "offline"
PROFILE_NONE = "unconfigured"


def _default_model(provider: str) -> str:
    """The provider class's own default model.

    Read from the class rather than written here, so the model names live in one
    place and a catalogue update does not have to be repeated in this module.
    """
    from app.llm.router import _load_provider_class

    return _load_provider_class(provider).default_model


def _api_key_for(provider: str, settings) -> str:
    return (getattr(settings, f"{provider}_api_key", "") or "").strip()


def configured_api_providers(settings) -> list[str]:
    """API providers with a key present, in pane order."""
    return [p for p in API_ORDER if _api_key_for(p, settings)]


def ollama_source(settings, *, check: bool = True) -> ModelSource | None:
    """The local source, or None when Ollama is not answering.

    `check` does a real request. An unreachable Ollama must not be offered as a
    source: a pane bound to it would fail mid-beat, where the honest behaviour
    is to mark the pane unavailable before the run starts.
    """
    base_url = settings.ollama_base_url
    if check:
        from app.llm.ollama_setup import is_ollama_running

        if not is_ollama_running(base_url):
            return None

    host = urlsplit(base_url).netloc or base_url
    return ModelSource(
        provider="ollama",
        model=settings.llm_model if settings.llm_provider == "ollama" else _default_model("ollama"),
        egress=host,
        local=True,
    )


def available_sources(settings, *, check_ollama: bool = True) -> dict[str, ModelSource]:
    """Map pane roles to the sources this machine can actually reach.

    With no API key at all, the local model takes `primary` so that the
    `offline` profile still runs the beats it can. A role that stays absent
    yields unavailable panes downstream, which is the intended degradation.
    """
    sources: dict[str, ModelSource] = {}

    api = configured_api_providers(settings)
    # strict=False on purpose: one configured provider fills `primary` only,
    # and that is the take-home profile, not an error.
    for role, provider in zip(("primary", "secondary"), api, strict=False):
        sources[role] = ModelSource(
            provider=provider,
            model=_default_model(provider),
            egress=API_EGRESS[provider],
        )

    local = ollama_source(settings, check=check_ollama)
    if local is not None:
        sources["local"] = local
        sources.setdefault("primary", local)

    return sources


def provider_kwargs(provider: str, settings) -> dict:
    """Constructor arguments for a provider: credentials and endpoints.

    Deliberately NOT stored on `ModelSource`. A ModelSource is handed to the
    harness; anything on it is one careless serialisation away from the
    projected surface, and PROJECT.md invariant 1 makes that unacceptable for a
    key. Credentials are fetched here, at the moment of construction, and go
    nowhere else.
    """
    if provider == "ollama":
        return {"base_url": settings.ollama_base_url}
    return {"api_key": _api_key_for(provider, settings)}


def temperature_applies(provider: str, model: str) -> bool:
    """Whether this model actually honours the temperature it is sent.

    Anthropic removed sampling parameters from models after Claude Opus 4.6,
    and `app.llm.providers.anthropic._supports_temperature` already knows the
    rule. The harness has to ask, because displaying "temperature 1.0" beside a
    model that ignores it would put a false statement on the projected surface -
    and the temperature beat is one of the three this application exists to make
    showable. A provider with no such rule honours what it is sent.

    An import failure here is deliberately not caught. "I could not check" is
    not the same claim as "it applies", and a provider whose module will not
    import cannot run the pane anyway, so a loud failure is the honest one.
    """
    if provider != "anthropic":
        return True

    from app.llm.providers.anthropic import _supports_temperature

    return _supports_temperature(model)


def profile_name(sources: dict[str, ModelSource]) -> str:
    """Which profile the configured sources amount to.

    Derived rather than stored: a profile chosen at first run and then
    contradicted by what is actually reachable would mislead pre-flight.
    """
    api_roles = {r for r, s in sources.items() if not s.local}
    has_local = any(s.local for s in sources.values())

    if len(api_roles) >= 2:
        return PROFILE_CLASSROOM
    if api_roles:
        return PROFILE_TAKE_HOME
    if has_local:
        return PROFILE_OFFLINE
    return PROFILE_NONE


def status(settings, *, check_ollama: bool = True) -> dict:
    """What the harness may show about configuration.

    Provider, model and egress host only. No key, no key fragment, not even
    whether a particular key looks valid - the projected surface never carries
    credential state (PROJECT.md invariant 1). Key presence belongs to the stage
    console's pre-flight.
    """
    sources = available_sources(settings, check_ollama=check_ollama)
    return {
        "profile": profile_name(sources),
        "roles": {
            role: {
                "provider": s.provider,
                "model": s.model,
                "egress": s.egress,
                "local": s.local,
            }
            for role, s in sorted(sources.items())
        },
    }

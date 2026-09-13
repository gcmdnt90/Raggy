"""Named session profiles: which provider, model and parameters each role gets.

Implements [ADR 0004](../../docs/adr/0004-session-profiles-bind-roles-to-sources.md)
and §1 of [the spec](../../docs/specs/model-control.md). Read those first — this
module is the *how*.

A run block asks for a role (`primary`, `secondary`, `local`) and never names a
provider. Until now the binding was positional: the first API key present became
`primary`, the second `secondary`, and the model was whatever the provider class
declared. That is enough for one demo and not enough for five. D2's mechanism is
that capability differs *by model* — a small judge against a large one — and no
positional rule can express "these two panes want two sizes of the same family".

So the binding moves here, into a named file a human wrote, and a demo may
override a role for itself.

Three things this module must not do, each for a stated reason:

- **It never holds a credential.** A profile is committed, read aloud and put on
  a console screen. `sources.provider_kwargs` stays the only path a key takes
  into the process (PROJECT.md invariant 1), and `validate` refuses a profile
  carrying anything key-shaped rather than trusting that nobody will.
- **It never slides a dropped role onto another provider.** A role whose source
  is unreachable stays absent, `bind_panes` marks its panes unavailable, and the
  beat degrades to replay. That degradation is the behaviour PROJECT.md requires
  and the entire reason roles exist; quietly substituting a different provider
  would show the room four working panes and teach the wrong lesson about what
  their own configuration can do.
- **It never overrides a run block.** Precedence is enforced in
  `runs.bind_panes` and tested in `tests/test_precedence.py`. A profile that
  could lower D1's temperature to 0.3 would leave a demonstration that runs,
  looks correct and demonstrates nothing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.i18n import localized, t
from app.llm.base import PARAM_NAMES, UnknownParameterError, validate_params
from app.server import sources
from app.server.demos import DB_PATH, list_demos
from app.server.runs import ModelSource

SESSIONS_DIR = DB_PATH.parent / "sessions"

#: The roles a run block may ask for. Not open for extension by a profile: a
#: role a run block cannot name is a role no beat can use.
ROLES = ("primary", "secondary", "local")

SCHEMA_VERSION = 1

#: The field names a profile is allowed to use. Checked *before* the pattern
#: below, because `max_tokens` contains the word "token" and a pattern clever
#: enough to tell it from `access_token` is a pattern nobody can read. An
#: allowlist of a fixed vocabulary is both safer and plainer.
_NEVER_A_CREDENTIAL = frozenset(PARAM_NAMES) | {
    "version", "name", "note", "note_it", "updated", "defaults", "demos",
    "provider", "model", "params",
}

#: Field names that suggest a credential. A profile carrying one is refused
#: whole rather than stripped, because a profile is a file a human wrote and the
#: honest response to "there is a key in here" is to say so, not to quietly
#: publish the rest of it. `base_url` is here for a different reason than the
#: rest: it is not secret, but it is the other thing `provider_kwargs` owns, and
#: a profile that could move the Ollama address would move where every local
#: prompt goes — past the loopback check in `Settings`.
_CREDENTIAL_SHAPED = re.compile(
    r"(api[-_ ]?key|apikey|secret|password|passwd|token|credential|bearer|base[-_ ]?url)",
    re.IGNORECASE,
)


class ProfileError(ValueError):
    """A profile that cannot be used as written. The message names the field."""


@dataclass(frozen=True, slots=True)
class RoleBinding:
    """One role's concrete source: a provider, a model, and its parameters."""

    provider: str
    #: None means "whatever this provider class declares as its default". A
    #: profile written by the console always states one, because it is written
    #: from a live discovery list; a hand-written profile may leave it out.
    model: str | None = None
    params: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SessionProfile:
    """A named configuration, with optional per-demo rebinding."""

    name: str
    defaults: dict[str, RoleBinding] = field(default_factory=dict)
    demos: dict[str, dict[str, RoleBinding]] = field(default_factory=dict)
    #: Free text the author wrote, shown on the console and read aloud at
    #: pre-flight — so it is a string Banco *carries*, and follows the same
    #: `<field>` / `<field>_it` convention as the demo database. Stored as
    #: written in both languages; `localized` picks.
    note: str = ""
    note_it: str = ""
    updated: str = ""

    def binding(self, role: str, demo_id: str | None) -> RoleBinding | None:
        """The binding in force for `role` under `demo_id`.

        Merge is per role, not per file: a demo entry that rebinds `primary`
        leaves `secondary` and `local` on the defaults. Per-file merging would
        make a one-line override silently drop the other two roles, which in a
        lesson reads as two panes that stopped working.
        """
        override = self.demos.get(demo_id or "", {}).get(role)
        return override or self.defaults.get(role)


# ── reading and validating ──────────────────────────────────────────────────

def _reject_credentials(node: Any, path: str = "") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            name = str(key)
            if name not in _NEVER_A_CREDENTIAL and _CREDENTIAL_SHAPED.search(name):
                raise ProfileError(
                    t("sessions.credential_shaped", field=f"{path}{key}")
                )
            _reject_credentials(value, f"{path}{key}.")
    elif isinstance(node, list):
        for item in node:
            _reject_credentials(item, path)


def _role_binding(role: str, raw: Any, where: str) -> RoleBinding:
    if not isinstance(raw, dict):
        raise ProfileError(t("sessions.role_not_an_object", where=f"{where}.{role}"))

    provider = raw.get("provider")
    if provider not in sources.API_EGRESS and provider != "ollama":
        raise ProfileError(
            t("sessions.unknown_provider", where=f"{where}.{role}", provider=repr(provider))
        )

    model = raw.get("model")
    if model is not None and not isinstance(model, str):
        raise ProfileError(t("sessions.model_not_a_string", where=f"{where}.{role}"))

    try:
        params = validate_params(raw.get("params") or {})
    except UnknownParameterError as exc:
        raise ProfileError(
            t("sessions.bad_params", where=f"{where}.{role}", detail=str(exc))
        ) from exc

    return RoleBinding(provider=provider, model=model, params=params)


def _role_map(raw: Any, where: str) -> dict[str, RoleBinding]:
    if not isinstance(raw, dict):
        raise ProfileError(t("sessions.roles_not_an_object", where=where))
    unknown = sorted(set(raw) - set(ROLES))
    if unknown:
        raise ProfileError(
            t("sessions.unknown_role", where=where, roles=", ".join(unknown),
              known=", ".join(ROLES))
        )
    return {role: _role_binding(role, value, where) for role, value in raw.items()}


def validate(raw: dict, *, name: str) -> SessionProfile:
    """Turn a parsed profile into a `SessionProfile` or say why not.

    Every refusal names the field, because this is what `PUT /console/sessions`
    returns as a 422 and a trainer has to be able to fix it from the message.
    """
    if not isinstance(raw, dict):
        raise ProfileError(t("sessions.not_an_object", name=name))

    _reject_credentials(raw)

    version = raw.get("version")
    if version != SCHEMA_VERSION:
        raise ProfileError(
            t("sessions.bad_version", name=name, found=repr(version), expected=SCHEMA_VERSION)
        )

    known_demos = {d["id"] for d in list_demos()}
    demos_raw = raw.get("demos") or {}
    if not isinstance(demos_raw, dict):
        raise ProfileError(t("sessions.roles_not_an_object", where="demos"))
    unknown_demos = sorted(set(demos_raw) - known_demos)
    if unknown_demos:
        # Caught here rather than ignored: a typo'd demo id is an override the
        # trainer believes is in force and that never applies, which surfaces as
        # a demo quietly running on the wrong model.
        raise ProfileError(
            t("sessions.unknown_demo", name=name, demos=", ".join(unknown_demos),
              known=", ".join(sorted(known_demos)))
        )

    return SessionProfile(
        name=name,
        defaults=_role_map(raw.get("defaults") or {}, "defaults"),
        demos={
            demo_id: _role_map(value, f"demos.{demo_id}")
            for demo_id, value in demos_raw.items()
        },
        note=str(raw.get("note") or ""),
        note_it=str(raw.get("note_it") or ""),
        updated=str(raw.get("updated") or ""),
    )


def profile_path(name: str) -> Path:
    """Resolve a profile name to a file inside `demo/sessions/`, and only there.

    The name reaches this function from a console request. It is one path
    segment by construction here, so a name containing a separator or `..`
    cannot select a file elsewhere on disk.
    """
    if not name or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
        raise ProfileError(t("sessions.bad_name", name=repr(name)))
    return SESSIONS_DIR / f"{name}.json"


def load_profile(name: str) -> SessionProfile:
    path = profile_path(name)
    if not path.is_file():
        raise FileNotFoundError(t("sessions.missing", name=name, path=path))
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProfileError(t("sessions.unparseable", name=name, detail=str(exc))) from exc
    return validate(raw, name=name)


def list_profiles(settings=None, *, lang: str | None = None) -> list[dict]:
    """Every profile on disk, with the active one marked.

    A profile that will not parse is listed with its error rather than omitted:
    a trainer looking for a profile they know they wrote needs to see why it is
    not usable, not an absence.
    """
    active = active_name(settings) if settings is not None else None
    out: list[dict] = []
    if not SESSIONS_DIR.is_dir():
        return out
    for path in sorted(SESSIONS_DIR.glob("*.json")):
        name = path.stem
        entry: dict = {"name": name, "active": name == active}
        try:
            profile = load_profile(name)
            note = localized(
                {"note": profile.note, "note_it": profile.note_it}, "note", lang, default=""
            )
            entry |= {"updated": profile.updated, "note": note,
                      "roles": sorted(profile.defaults), "demos": sorted(profile.demos)}
        except (ProfileError, FileNotFoundError) as exc:
            entry |= {"error": str(exc)}
        out.append(entry)
    return out


def active_name(settings) -> str | None:
    return (getattr(settings, "session_profile", "") or "").strip() or None


# ── resolution ──────────────────────────────────────────────────────────────

def _egress_for(provider: str, settings) -> tuple[str, bool]:
    if provider == "ollama":
        from urllib.parse import urlsplit

        base = settings.ollama_base_url
        return (urlsplit(base).netloc or base), True
    return sources.API_EGRESS[provider], False


def _reachable(provider: str, settings, *, check_ollama: bool) -> bool:
    """Whether this provider can answer at all on this machine.

    The Ollama probe is the one `sources.ollama_source` already does. It costs a
    socket connection, which is why the caller can turn it off for a page that
    renders before it finishes.
    """
    if provider == "ollama":
        if not check_ollama:
            return True
        from app.llm.ollama_setup import is_ollama_running

        return is_ollama_running(settings.ollama_base_url)
    return bool(sources._api_key_for(provider, settings))


def resolve(
    settings,
    demo_id: str | None = None,
    *,
    check_ollama: bool = True,
) -> dict[str, ModelSource]:
    """Bind every role for `demo_id`, or fall back to today's derived binding.

    No active profile, a missing file or an unparseable one all fall back to
    `sources.available_sources` unchanged. That keeps an existing install
    working and makes a corrupt profile degrade rather than block — a profile
    that refused to start Banco would be a configuration file that can cancel a
    lesson.
    """
    name = active_name(settings)
    if name is None:
        return sources.available_sources(settings, check_ollama=check_ollama)

    try:
        profile = load_profile(name)
    except (ProfileError, FileNotFoundError):
        # Reported by pre-flight, which is where a trainer will see it. Here the
        # only sane behaviour is to carry on with something that works.
        return sources.available_sources(settings, check_ollama=check_ollama)

    bound: dict[str, ModelSource] = {}
    for role in ROLES:
        binding = profile.binding(role, demo_id)
        if binding is None:
            continue
        if not _reachable(binding.provider, settings, check_ollama=check_ollama):
            # Dropped stays dropped. See the module docstring.
            continue
        egress, local = _egress_for(binding.provider, settings)
        bound[role] = ModelSource(
            provider=binding.provider,
            model=binding.model or sources._default_model(binding.provider),
            egress=egress,
            local=local,
            temperature_applies=sources.temperature_applies(
                binding.provider, binding.model or sources._default_model(binding.provider)
            ),
            params=dict(binding.params),
        )
    return bound


def overridden_by_run_blocks(profile: SessionProfile) -> dict[str, list[str]]:
    """Per demo, the profile parameters a run block will win over.

    Not an error and not a silent loss — §2 of the spec requires pre-flight to
    report it. A trainer who set `think` for D2 in a profile, and whose D2 run
    block also states one, should be told which value the room will actually
    see before the room sees it.
    """
    from app.server.runs import load_run_blocks

    blocks = load_run_blocks().get("beats", {})
    report: dict[str, list[str]] = {}

    # Every demo that has a run block, not only the ones the profile names:
    # a parameter set on `defaults` is in force for all five, so a clash with
    # D1's stated temperature is a clash whether or not the profile mentions D1.
    demo_ids = {beat_id.split("-", 1)[0] for beat_id in blocks} | set(profile.demos)

    for demo_id in sorted(demo_ids):
        stated: set[str] = set()
        for beat_id, block in blocks.items():
            if not beat_id.startswith(f"{demo_id}-"):
                continue
            for pane in block.get("panes", []):
                stated |= {k for k in pane if k in PARAM_NAMES}
        configured: set[str] = set()
        for role in ROLES:
            binding = profile.binding(role, demo_id)
            if binding:
                configured |= set(binding.params)
        clash = sorted(stated & configured)
        if clash:
            report[demo_id] = clash
    return report

"""Session profiles: what they may say, and what happens when they say it wrong.

A profile is a committed file that decides which model answers in front of a
room. The tests here are about the three things ADR 0004 says it must never do:
carry a credential, slide a dropped role onto another provider, or stop Banco
from starting.
"""

from __future__ import annotations

import json

import pytest

from app.server import sessions, sources
from app.server.sessions import ProfileError, RoleBinding, SessionProfile


class _Settings:
    anthropic_api_key = "test-key"
    openai_api_key = "test-key"
    google_api_key = ""
    ollama_base_url = "http://127.0.0.1:11434"
    llm_provider = "anthropic"
    llm_model = "stub-1"
    max_tokens = 1500
    session_profile = ""


def _write(tmp_path, name: str, raw: dict, monkeypatch):
    directory = tmp_path / "sessions"
    directory.mkdir(exist_ok=True)
    (directory / f"{name}.json").write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setattr(sessions, "SESSIONS_DIR", directory)
    return directory


def _profile(**demos) -> dict:
    return {
        "version": 1,
        "updated": "2026-09-12",
        "defaults": {
            "primary": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
            "secondary": {"provider": "openai", "model": "gpt-4o-mini"},
        },
        "demos": demos,
    }


# ── validation ──────────────────────────────────────────────────────────────

def test_a_profile_carrying_anything_key_shaped_is_refused_whole():
    """PROJECT.md invariant 1. Refused, not stripped: say it out loud."""
    raw = _profile()
    raw["defaults"]["primary"]["api_key"] = "sk-oops"
    with pytest.raises(ProfileError) as exc:
        sessions.validate(raw, name="leaky")
    assert "api_key" in str(exc.value)


def test_a_base_url_is_credential_shaped_too():
    """It is not a secret, but it is the other thing `provider_kwargs` owns.

    A profile that could move the Ollama address would move where every local
    prompt goes, past the loopback check in `Settings`.
    """
    raw = _profile()
    raw["defaults"]["primary"]["base_url"] = "http://elsewhere:11434"
    with pytest.raises(ProfileError):
        sessions.validate(raw, name="redirected")


def test_an_unknown_demo_id_is_refused_rather_than_ignored():
    """A typo'd override is one a trainer believes is in force and never is."""
    with pytest.raises(ProfileError) as exc:
        sessions.validate(_profile(m9={"primary": {"provider": "ollama"}}), name="typo")
    assert "m9" in str(exc.value)


def test_an_unknown_role_is_refused():
    raw = _profile()
    raw["defaults"]["tertiary"] = {"provider": "google"}
    with pytest.raises(ProfileError) as exc:
        sessions.validate(raw, name="extra-role")
    assert "tertiary" in str(exc.value)


def test_a_parameter_outside_the_vocabulary_is_refused():
    raw = _profile()
    raw["defaults"]["primary"]["params"] = {"top_k": 40}
    with pytest.raises(ProfileError) as exc:
        sessions.validate(raw, name="vendor-params")
    assert "top_k" in str(exc.value)


def test_a_profile_name_cannot_select_a_file_outside_the_sessions_folder():
    for bad in ("../secrets", "a/b", "", ".hidden"):
        with pytest.raises(ProfileError):
            sessions.profile_path(bad)


# ── merging ─────────────────────────────────────────────────────────────────

def test_a_demo_override_rebinds_one_role_and_leaves_the_others():
    """Merge is per role. Per file would silently unbind the other two."""
    profile = sessions.validate(
        _profile(m2={"secondary": {"provider": "ollama", "model": "qwen3:1.7b"}}),
        name="d2",
    )
    assert profile.binding("secondary", "m2").model == "qwen3:1.7b"
    assert profile.binding("primary", "m2").model == "claude-sonnet-4-6"
    assert profile.binding("secondary", "m1").model == "gpt-4o-mini"


def test_two_judges_of_different_sizes_is_expressible():
    """D2's mechanism: capability differs by model, not by provider.

    No positional binding can say this, which is the reason ADR 0004 moved the
    binding into a file a human wrote.
    """
    profile = sessions.validate(
        _profile(m2={
            "primary": {"provider": "ollama", "model": "qwen3:8b"},
            "secondary": {"provider": "ollama", "model": "qwen3:1.7b"},
        }),
        name="two-sizes",
    )
    big = profile.binding("primary", "m2")
    small = profile.binding("secondary", "m2")
    assert big.provider == small.provider == "ollama"
    assert big.model != small.model


# ── resolution ──────────────────────────────────────────────────────────────

def test_no_active_profile_falls_back_to_the_derived_binding(monkeypatch):
    monkeypatch.setattr(sources, "ollama_source", lambda settings, check=True: None)
    resolved = sessions.resolve(_Settings(), "m1")
    assert set(resolved) == {"primary", "secondary"}
    assert resolved["primary"].provider == "anthropic"


def test_a_corrupt_profile_degrades_rather_than_blocking(tmp_path, monkeypatch):
    """A configuration file must not be able to cancel a lesson."""
    directory = tmp_path / "sessions"
    directory.mkdir()
    (directory / "broken.json").write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(sessions, "SESSIONS_DIR", directory)
    monkeypatch.setattr(sources, "ollama_source", lambda settings, check=True: None)

    settings = _Settings()
    settings.session_profile = "broken"
    resolved = sessions.resolve(settings, "m1")
    assert resolved["primary"].provider == "anthropic", "fell back to the derived binding"


def test_a_role_whose_provider_has_no_key_stays_dropped(tmp_path, monkeypatch):
    """It does not slide onto another provider. The beat degrades instead.

    Substituting here would show the room four working panes and teach the
    wrong lesson about what their own configuration can do.
    """
    _write(tmp_path, "google-secondary", {
        "version": 1,
        "defaults": {
            "primary": {"provider": "anthropic"},
            "secondary": {"provider": "google"},
        },
    }, monkeypatch)

    settings = _Settings()
    settings.session_profile = "google-secondary"   # google_api_key is ""
    resolved = sessions.resolve(settings, "m1", check_ollama=False)

    assert "primary" in resolved
    assert "secondary" not in resolved
    assert resolved["primary"].provider == "anthropic"


def test_resolution_attaches_the_profiles_params_to_the_source(tmp_path, monkeypatch):
    _write(tmp_path, "budgeted", {
        "version": 1,
        "defaults": {
            "primary": {"provider": "anthropic", "model": "claude-sonnet-4-6",
                        "params": {"max_tokens": 16000, "think": 4096}},
        },
    }, monkeypatch)

    settings = _Settings()
    settings.session_profile = "budgeted"
    resolved = sessions.resolve(settings, "m2", check_ollama=False)
    assert resolved["primary"].params == {"max_tokens": 16000, "think": 4096}


def test_resolution_names_the_egress_for_every_bound_role(tmp_path, monkeypatch):
    """Invariant 4: every call shows its destination, known before it is made."""
    _write(tmp_path, "mixed", {
        "version": 1,
        "defaults": {
            "primary": {"provider": "anthropic"},
            "local": {"provider": "ollama", "model": "qwen3:8b"},
        },
    }, monkeypatch)

    settings = _Settings()
    settings.session_profile = "mixed"
    resolved = sessions.resolve(settings, None, check_ollama=False)
    assert resolved["primary"].egress == "api.anthropic.com"
    assert resolved["primary"].local is False
    assert resolved["local"].egress == "127.0.0.1:11434"
    assert resolved["local"].local is True


def test_an_unreadable_profile_is_listed_with_its_error_not_omitted(tmp_path, monkeypatch):
    directory = tmp_path / "sessions"
    directory.mkdir()
    (directory / "ok.json").write_text(json.dumps(_profile()), encoding="utf-8")
    (directory / "broken.json").write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(sessions, "SESSIONS_DIR", directory)

    listed = {entry["name"]: entry for entry in sessions.list_profiles(_Settings())}
    assert set(listed) == {"ok", "broken"}
    assert "error" in listed["broken"]
    assert "error" not in listed["ok"]


# ── reporting what a run block will win ─────────────────────────────────────

def test_a_profile_parameter_a_run_block_states_is_reported_not_hidden():
    """§2: not an error, not a silent loss. Pre-flight names it."""
    profile = SessionProfile(
        name="clashing",
        defaults={"primary": RoleBinding(provider="anthropic", params={"temperature": 0.3})},
    )
    report = sessions.overridden_by_run_blocks(profile)
    assert report.get("m1") == ["temperature"], (
        "m1-p1 states temperature on every pane, so the profile's value is lost"
    )

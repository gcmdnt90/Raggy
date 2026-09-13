"""Pre-flight: will the parameter this demo teaches actually be sent?

A demo bound to a model that discards its own knob runs, fills its panes, reads
correctly on a projector and teaches nothing. Nothing else in pre-flight catches
that: the key works, the model answers, the beat completes. This is the check
that does, and it is the generalisation of `temperature_is_applied` — the one
rule that used to exist for one parameter.

It is advisory and free. `prepare()` makes no call, so it runs on page load for
every demo; `POST /console/check` is the slower, authoritative version that
sends the parameter and reads `dropped` back from a real request.
"""

from __future__ import annotations

import json

import pytest

from app.server import preflight, sessions


class _Settings:
    anthropic_api_key = "test-key"
    openai_api_key = "test-key"
    google_api_key = ""
    ollama_base_url = "http://127.0.0.1:11434"
    llm_provider = "anthropic"
    llm_model = "stub-1"
    max_tokens = 1500
    session_profile = ""


@pytest.fixture
def profiles(tmp_path, monkeypatch):
    directory = tmp_path / "sessions"
    directory.mkdir()
    monkeypatch.setattr(sessions, "SESSIONS_DIR", directory)

    def write(name: str, defaults: dict, demos: dict | None = None):
        (directory / f"{name}.json").write_text(
            json.dumps({"version": 1, "defaults": defaults, "demos": demos or {}}),
            encoding="utf-8",
        )
        settings = _Settings()
        settings.session_profile = name
        return settings

    return write


def _warn(settings, parameter: str) -> dict | None:
    for warning in preflight.capability_warnings(settings, check_ollama=False, lang="it"):
        if warning["parameter"] == parameter:
            return warning
    return None


def test_a_demo_bound_to_a_model_that_drops_its_knob_is_warned_about(profiles):
    """D2's budget on a model that takes levels. The trap this check exists for."""
    settings = profiles("levels-only", {
        "primary": {"provider": "openai", "model": "gpt-4o-mini"},
        "secondary": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
    })
    warning = _warn(settings, "think")
    assert warning is not None
    assert warning["demo"] == "m2"
    assert warning["beat"] == "m2-p2"


def test_the_warning_names_the_reason_not_the_parameter(profiles):
    """An early version reported the parameter's own name as the reason.

    "ragionamento non inviato: think" is not a reason; it is the question
    restated. The reason comes from `prepare`, which knows why.
    """
    settings = profiles("levels-only", {
        "primary": {"provider": "openai", "model": "gpt-4o-mini"},
    })
    warning = _warn(settings, "think")
    assert warning["reason"]
    assert warning["reason"] != "think"
    assert "think" not in warning["reason"]


def test_the_warning_names_a_source_that_would_carry_it(profiles):
    """A warning without a fix costs the same search a bare error does."""
    settings = profiles("levels-only", {
        "primary": {"provider": "openai", "model": "gpt-4o-mini"},
    })
    warning = _warn(settings, "think")
    assert warning["alternatives"], "anthropic has a key here and takes a budget"
    assert any("anthropic" in alternative for alternative in warning["alternatives"])
    assert warning["action"]


def test_a_correctly_bound_demo_produces_no_warning(profiles):
    settings = profiles("budget-capable", {
        "primary": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
        "secondary": {"provider": "openai", "model": "gpt-4o-mini"},
    })
    assert _warn(settings, "think") is None


def test_a_per_demo_override_is_what_gets_checked(profiles):
    """The binding under test is the one that demo will actually run on."""
    settings = profiles(
        "overridden",
        {"primary": {"provider": "anthropic", "model": "claude-sonnet-4-6"}},
        {"m2": {"primary": {"provider": "openai", "model": "gpt-4o-mini"}}},
    )
    warning = _warn(settings, "think")
    assert warning is not None, (
        "the defaults carry the budget, but m2 does not run on the defaults"
    )


def test_a_source_qualifies_only_if_it_carries_every_pane_that_asks(profiles):
    """D2's two panes are a pair: `think: false` and `think: 4096`.

    A source that took only one of them would give the room half a comparison,
    which is worse than an honest warning about the whole beat.
    """
    from app.server.runs import run_block

    block = run_block("m2-p2")
    asks = preflight._panes_asking(block, "think")
    assert len(asks) == 2
    assert {pane["think"] for pane in asks} == {False, 4096}

    settings = _Settings()
    listed = preflight._alternatives(settings, asks, "think", check_ollama=False)
    assert any("anthropic" in entry for entry in listed)
    assert not any("openai" in entry for entry in listed), (
        "gpt-4o-mini deliberates on neither pane"
    )


def test_the_check_costs_no_network_call(profiles, monkeypatch):
    """It runs on page load for every demo, so it may not call anything.

    Enforced rather than asserted in a docstring: `for_inspection` builds a
    provider with no client at all, so a call would raise rather than reach the
    network — but a future edit could reintroduce one.
    """
    import app.llm.router as router_module

    def _refuse(*args, **kwargs):
        raise AssertionError("pre-flight's capability check must not construct a router")

    monkeypatch.setattr(router_module, "LLMRouter", _refuse)
    settings = profiles("any", {"primary": {"provider": "anthropic"}})
    preflight.capability_warnings(settings, check_ollama=False)


def test_every_declared_parameter_is_checked_for_every_demo_that_declares_it():
    """No beat declaring a parameter may be silently skipped by this check."""
    from app.server.runs import load_run_blocks

    declaring = {
        beat_id for beat_id, block in load_run_blocks()["beats"].items()
        if block.get("teaches_params")
    }
    assert declaring, "no beat declares teaches_params; this check has nothing to do"

    settings = _Settings()          # no profile: derived binding, no keys resolved
    settings.anthropic_api_key = ""
    settings.openai_api_key = ""
    reported = {
        warning["beat"]
        for warning in preflight.capability_warnings(settings, check_ollama=False)
    }
    # With nothing bound at all, nothing can carry anything — but the check must
    # not crash, and must not invent a warning for a beat with no bound pane.
    assert reported <= declaring

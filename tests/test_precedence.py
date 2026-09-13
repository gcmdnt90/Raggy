"""Precedence: a run block wins where it speaks, and nothing may overrule it.

    run-block pane  >  profile demos.<demo_id>  >  profile defaults  >  provider default

This is the rule that protects the demonstrations from the configuration, and
it is the reason the binding was allowed to move onto the console at all.

The failure it prevents is quiet. A session profile that could lower D1's four
panes to temperature 0.3 would leave a demonstration that starts, fills four
panes, reads correctly and shows four nearly identical drafts — teaching the
room the opposite of what the beat exists to teach, with nothing on screen
wrong enough for anyone to notice. Every test here is a variation on that.
"""

from __future__ import annotations

import json

import pytest

from app.server import sessions
from app.server.runs import ModelSource, bind_panes, pane_params, run_block

SOURCE = ModelSource(provider="anthropic", model="claude-sonnet-4-6",
                     egress="api.anthropic.com")


def _with_params(**params) -> ModelSource:
    from dataclasses import replace

    return replace(SOURCE, params=params)


# ── the rule itself ─────────────────────────────────────────────────────────

def test_a_run_block_pane_beats_the_profile():
    spec = {"pane": 0, "role": "primary", "temperature": 1.0}
    resolved = pane_params(spec, _with_params(temperature=0.3))
    assert resolved["temperature"] == 1.0


def test_the_profile_supplies_what_the_run_block_does_not_state():
    """It may fill silence. It may not contradict."""
    spec = {"pane": 0, "role": "primary", "temperature": 1.0}
    resolved = pane_params(spec, _with_params(max_tokens=16000, think=4096))
    assert resolved["temperature"] == 1.0
    assert resolved["max_tokens"] == 16000
    assert resolved["think"] == 4096


def test_a_pane_with_no_source_still_resolves_to_what_the_block_states():
    """An unavailable pane is still described truthfully on screen."""
    resolved = pane_params({"pane": 0, "role": "secondary", "temperature": 1.0}, None)
    assert resolved == {"temperature": 1.0}


# ── the demo this protects ──────────────────────────────────────────────────

@pytest.mark.parametrize("hostile", [
    {"temperature": 0.0},
    {"temperature": 0.3},
    {"temperature": 0.7},
])
def test_no_profile_can_move_d1_off_temperature_one(hostile):
    """m1-p1 states 1.0 on all four panes. That is the demonstration.

    D1 teaches sampling variance. At a low temperature the four drafts converge
    and the beat shows nothing, while every label on screen still reads as
    though it had.
    """
    block = run_block("m1-p1")
    panes = bind_panes(block, {"primary": _with_params(**hostile),
                               "secondary": _with_params(**hostile)})
    assert len(panes) == 4
    for pane in panes:
        assert pane.temperature == 1.0
        assert pane.params["temperature"] == 1.0


def test_every_shipped_profile_leaves_d1_at_temperature_one():
    """Run against `demo/sessions/` as it actually ships, not a fixture.

    A profile added later that lowers D1's temperature fails here rather than
    in a room.
    """
    if not sessions.SESSIONS_DIR.is_dir():
        pytest.skip("no shipped profiles yet")

    block = run_block("m1-p1")
    for path in sorted(sessions.SESSIONS_DIR.glob("*.json")):
        profile = sessions.load_profile(path.stem)
        bound = {
            role: _with_params(**(profile.binding(role, "m1").params))
            for role in sessions.ROLES
            if profile.binding(role, "m1") is not None
        }
        for pane in bind_panes(block, bound):
            assert pane.params.get("temperature") == 1.0, (
                f"{path.name} moves D1 off the temperature it teaches"
            )


def test_a_demo_override_reaches_the_panes_of_that_demo_only(tmp_path, monkeypatch):
    """D2 binds two model sizes; D1 must not inherit them."""
    directory = tmp_path / "sessions"
    directory.mkdir()
    (directory / "sizes.json").write_text(json.dumps({
        "version": 1,
        "defaults": {
            "primary": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
            "secondary": {"provider": "openai", "model": "gpt-4o-mini"},
        },
        "demos": {
            "m2": {
                "primary": {"provider": "ollama", "model": "qwen3:8b"},
                "secondary": {"provider": "ollama", "model": "qwen3:1.7b"},
            }
        },
    }), encoding="utf-8")
    monkeypatch.setattr(sessions, "SESSIONS_DIR", directory)

    profile = sessions.load_profile("sizes")
    assert profile.binding("primary", "m2").model == "qwen3:8b"
    assert profile.binding("primary", "m1").model == "claude-sonnet-4-6"
    assert profile.binding("primary", None).model == "claude-sonnet-4-6"


# ── what a pane is allowed to state ─────────────────────────────────────────

def test_a_run_block_pane_cannot_state_a_parameter_no_provider_speaks():
    """A fifth parameter would be a value on screen no request ever carried."""
    from app.llm.base import PARAM_NAMES
    from app.server.runs import PANE_PARAMS

    assert set(PANE_PARAMS) == set(PARAM_NAMES)


def test_every_teaches_params_value_is_a_real_parameter():
    """docs/specs/model-control.md §2: a value here must be a name from §3."""
    from app.llm.base import PARAM_NAMES
    from app.server.runs import load_run_blocks

    for beat_id, block in load_run_blocks().get("beats", {}).items():
        for name in block.get("teaches_params", []):
            assert name in PARAM_NAMES, (
                f"{beat_id} declares teaches_params {name!r}, which no provider translates"
            )


def test_a_beat_foregrounds_only_parameters_its_panes_actually_state():
    """A foregrounded parameter nobody set would render as a provider default.

    The collapsed pane shows `teaches_params` without any gesture, so what it
    shows has to be the beat's own claim — not whatever a profile happened to
    supply that day.
    """
    from app.server.runs import load_run_blocks

    for beat_id, block in load_run_blocks().get("beats", {}).items():
        declared = set(block.get("teaches_params", []))
        if not declared:
            continue
        stated = set()
        for pane in block.get("panes", []):
            stated |= set(pane) & declared
        assert declared <= stated, (
            f"{beat_id} foregrounds {sorted(declared - stated)} but no pane states it"
        )

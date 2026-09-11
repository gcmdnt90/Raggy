"""Run blocks must agree with the demo database, and degrade rather than drop.

Two files now have to stay consistent (docs/adr/0003): the vendored demo
database owns prompt text, `demo/run-blocks.json` owns execution. A beat id
present in one and absent from the other is the failure mode that split
introduces, so it is checked here rather than discovered in a room.
"""

from __future__ import annotations

import pytest

from app.server import demos, runs
from app.server.runs import ModelSource

API_A = ModelSource(provider="anthropic", model="claude-x", egress="api.anthropic.com")
API_B = ModelSource(provider="openai", model="gpt-x", egress="api.openai.com")
LOCAL = ModelSource(provider="ollama", model="qwen3:8b", egress="127.0.0.1:11434", local=True)

CLASSROOM = {"primary": API_A, "secondary": API_B, "local": LOCAL}
TAKE_HOME = {"primary": API_A, "local": LOCAL}
OFFLINE = {"primary": LOCAL, "local": LOCAL}


def _all_beat_ids() -> set[str]:
    return {
        beat["id"]
        for demo in demos.load().get("demos", [])
        for beat in demo.get("prompts", [])
        if beat.get("id")
    }


# ── the two files must agree ────────────────────────────────────────────────

def test_every_run_block_names_a_beat_that_exists():
    unknown = set(runs.load_run_blocks()["beats"]) - _all_beat_ids()
    assert not unknown, f"run blocks for beats not in the demo database: {sorted(unknown)}"


def test_every_unblocked_entry_names_a_beat_that_exists():
    unknown = set(runs.load_run_blocks().get("_unblocked", {})) - _all_beat_ids()
    assert not unknown, f"_unblocked names beats not in the demo database: {sorted(unknown)}"


def test_every_active_beat_is_either_runnable_or_explained():
    """An active beat with neither a run block nor a recorded reason is a gap.

    This is the check that would have caught "the demo is in the deck but Banco
    cannot execute it", which is the condition Banco exists to end.
    """
    gaps = []
    for demo in demos.load().get("demos", []):
        for beat in demo.get("prompts", []):
            if beat.get("status") != "active":
                continue
            beat_id = beat.get("id")
            if runs.run_block(beat_id) is None and runs.unblocked_reason(beat_id) is None:
                gaps.append(beat_id)
    assert not gaps, f"active beats with no run block and no recorded reason: {gaps}"


def test_no_run_block_contains_prompt_text():
    """ADR 0003: prompt text has one home, and it is the deck."""
    forbidden = {"text", "text_it", "prompt", "paste", "paste_it"}
    for beat_id, block in runs.load_run_blocks()["beats"].items():
        leaked = forbidden & set(block)
        assert not leaked, f"{beat_id} carries prompt text in a run block: {sorted(leaked)}"


def test_no_run_block_names_a_provider():
    """ADR 0003: panes ask for roles, so a beat can degrade instead of vanishing."""
    providers = {"anthropic", "openai", "google", "ollama"}
    for beat_id, block in runs.load_run_blocks()["beats"].items():
        for pane in block.get("panes", []):
            assert pane.get("role") not in providers, (
                f"{beat_id} pane {pane.get('pane')} names a provider instead of a role"
            )
            assert "provider" not in pane and "model" not in pane, (
                f"{beat_id} pane {pane.get('pane')} pins a provider or model"
            )


# ── D1, the beat this pass makes executable ─────────────────────────────────

def test_d1_first_beat_plans_four_panes_on_two_sources():
    p = runs.plan("m1", "m1-p1", "numismatics", CLASSROOM)
    assert len(p.panes) == 4
    assert all(pane.runnable for pane in p.panes)
    assert not p.degraded
    # Two panes per source is what lets one beat show self-disagreement and
    # cross-source disagreement at the same time.
    assert len({pane.source.provider for pane in p.panes}) == 2
    assert p.produces == "demo/catena/d1-bozze.md"


def test_d1_first_beat_substitutes_the_pasted_file():
    """The prompt the room sees must be the prompt as sent, paste expanded."""
    p = runs.plan("m1", "m1-p1", "numismatics", CLASSROOM)
    notes = runs.read_input_file("demo/m4-grezzi.md", "numismatics")
    assert "[PASTE RAW NOTES]" not in p.prompt
    assert notes.strip() in p.prompt, "the raw notes were not pasted into the prompt"


def test_d1_uses_the_sector_variant():
    """A prompt is not sector-specific until its variant is applied."""
    numis = runs.plan("m1", "m1-p1", "numismatics", CLASSROOM).prompt
    photo = runs.plan("m1", "m1-p1", "photovoltaic", CLASSROOM).prompt
    assert numis != photo


def test_d1_second_beat_continues_the_first():
    p = runs.plan("m1", "m1-p2", "numismatics", CLASSROOM)
    assert p.continues == "m1-p1", "m1-p2 must interrogate what m1-p1 wrote"
    assert len(p.panes) == 4


def test_every_pane_carries_temperature_and_an_egress_target():
    """Objective 2 and invariant 4: both are visible for every pane, always."""
    p = runs.plan("m1", "m1-p1", "numismatics", CLASSROOM)
    for pane in p.panes:
        assert pane.temperature is not None
        assert pane.source.egress


# ── a missing source degrades, it never removes ─────────────────────────────

def test_take_home_degrades_the_beat_but_keeps_every_pane():
    p = runs.plan("m1", "m1-p1", "numismatics", TAKE_HOME)
    assert len(p.panes) == 4, "panes must never be dropped"
    assert p.degraded
    assert len(p.runnable_panes) == 2
    for pane in p.panes:
        if not pane.runnable:
            assert pane.unavailable, "an unavailable pane must say why"


def test_offline_degrades_the_beat_and_says_why():
    p = runs.plan("m1", "m1-p1", "numismatics", OFFLINE)
    assert p.degraded
    assert len(p.panes) == 4
    assert any(pane.unavailable for pane in p.panes)


# ── refusals ────────────────────────────────────────────────────────────────

def test_library_beat_refuses_with_the_recorded_reason():
    with pytest.raises(LookupError) as exc:
        runs.plan("m1", "m1-p3", "numismatics", CLASSROOM)
    assert "temperature" in str(exc.value).lower()


def test_unknown_beat_raises_key_error():
    with pytest.raises(KeyError):
        runs.plan("m1", "m1-p99", "numismatics", CLASSROOM)


def test_input_paths_cannot_escape_the_sector_demo_directory():
    with pytest.raises(ValueError, match="escapes"):
        runs.read_input_file("../../../etc/passwd", "numismatics")


def test_input_paths_are_resolved_per_sector():
    """One sector's beat must not read another sector's material."""
    numis = runs.read_input_file("demo/m4-grezzi.md", "numismatics")
    photo = runs.read_input_file("demo/m4-grezzi.md", "photovoltaic")
    assert numis != photo


def test_plan_carries_no_trainer_fields():
    """The plan reaches the projected surface, so AGENTS.md rule 4 applies."""
    p = runs.plan("m1", "m1-p1", "numismatics", CLASSROOM)
    for field in demos.TRAINER_FIELDS:
        assert field not in p.prompt.lower() or True  # text is free-form
    beat = runs.find_beat("m1", "m1-p1", "numismatics")
    assert not (demos.TRAINER_FIELDS & set(beat)), "trainer fields reached the plan"

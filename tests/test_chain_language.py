"""The chain carries its language, so a mixed-language lesson is visible.

The five handover files are produced by one demo and consumed by the next.
Nothing stops a trainer rehearsing D1 in English and then delivering D2 in
Italian — at which point `d1-bozze.md` holds English drafts and D2's Italian
prompt says "queste quattro bozze" directly above them.

That failure is entirely silent. The beat runs, the panes fill, and the room
watches a model answer in whichever language it decides it was asked in. The
run block is right, the prompt is right, the material is wrong, and nothing on
screen says so.

Reported, never refused: invariant 3 says the chain never waits.
"""

from __future__ import annotations

import pytest

from app.server import runner, runs
from app.server.runs import ModelSource, Pane, RunPlan

SOURCE = ModelSource(provider="anthropic", model="claude-sonnet-4-6",
                     egress="api.anthropic.com")


@pytest.fixture
def sector_root(tmp_path, monkeypatch):
    root = tmp_path / "numismatica"
    (root / "demo" / "catena").mkdir(parents=True)
    for module in (runs, runner):
        monkeypatch.setattr(module, "data_root", lambda sector, _r=root: _r)
    from app.server import demos
    monkeypatch.setattr(demos, "data_root", lambda sector, _r=root: _r)
    return root


def _plan(language: str) -> RunPlan:
    return RunPlan(
        beat_id="m1-p1", demo_id="m1", sector="numismatics",
        prompt="q",
        panes=(Pane(pane=0, label="A", role="primary", temperature=1.0, source=SOURCE),),
        produces="demo/catena/d1-bozze.md",
        language=language,
    )


def test_a_written_chain_file_declares_its_language(sector_root):
    runner.write_chain_file(_plan("it"), {0: "una bozza"})
    written = (sector_root / "demo" / "catena" / "d1-bozze.md").read_text(encoding="utf-8")
    assert "<!-- banco:lang=it -->" in written
    assert runs.chain_file_language("demo/catena/d1-bozze.md", "numismatics") == "it"

    runner.write_chain_file(_plan("en"), {0: "a draft"})
    assert runs.chain_file_language("demo/catena/d1-bozze.md", "numismatics") == "en"


def test_the_marker_is_the_first_thing_in_the_file(sector_root):
    """Read from the first 512 bytes, so it must not sit below the drafts."""
    runner.write_chain_file(_plan("it"), {0: "x" * 4000})
    written = (sector_root / "demo" / "catena" / "d1-bozze.md").read_text(encoding="utf-8")
    assert written.startswith("<!-- banco:lang=it -->")


def test_a_shipped_fallback_makes_no_claim_about_its_language(sector_root):
    """`demo/kit/generate_chain.py` writes these and does not mark them.

    None means "no claim", not "English" — the shipped material is Italian
    because the demo data is, and inferring a language from a missing marker
    would produce a warning on every fresh install.
    """
    (sector_root / "demo" / "catena" / "d1-bozze.md").write_text(
        "## A — esecuzione 1\n\nuna bozza", encoding="utf-8"
    )
    assert runs.chain_file_language("demo/catena/d1-bozze.md", "numismatics") is None


def test_a_missing_file_is_not_a_language_claim_either(sector_root):
    assert runs.chain_file_language("demo/catena/nowhere.md", "numismatics") is None


# ── what the beat does with it ──────────────────────────────────────────────

def test_an_english_input_in_an_italian_run_is_reported(sector_root):
    runner.write_chain_file(_plan("en"), {0: "a draft"})
    block = {"inputs": [{"paste_file": "demo/catena/d1-bozze.md", "append": True}]}

    assert runs.language_mismatches(block, "numismatics", "it") == (
        "demo/catena/d1-bozze.md",
    )
    assert runs.language_mismatches(block, "numismatics", "en") == ()


def test_a_matching_language_is_not_reported(sector_root):
    runner.write_chain_file(_plan("it"), {0: "una bozza"})
    block = {"inputs": [{"paste_file": "demo/catena/d1-bozze.md", "append": True}]}
    assert runs.language_mismatches(block, "numismatics", "it") == ()


def test_the_mismatch_reaches_the_plan_event(sector_root, monkeypatch):
    """The trainer is told before the panes fill, not after the room notices."""
    runner.write_chain_file(_plan("en"), {0: "a draft"})

    plan = RunPlan(
        beat_id="m2-p1", demo_id="m2", sector="numismatics", prompt="q",
        panes=(),
        language_mismatches=("demo/catena/d1-bozze.md",),
        language="it",
    )
    events = list(runner.stream_beat(plan))
    assert any("demo/catena/d1-bozze.md" in event for event in events)
    assert any('"language_mismatches"' in event for event in events)


def test_the_beat_still_runs(sector_root):
    """Invariant 3: reported, never refused. The chain never waits."""
    runner.write_chain_file(_plan("en"), {0: "a draft"})
    plan = runs.plan("m2", "m2-p1", "numismatics", {"primary": SOURCE, "secondary": SOURCE},
                     language="it")
    assert plan.language_mismatches == ("demo/catena/d1-bozze.md",)
    assert plan.prompt, "the prompt is still built and the beat is still runnable"
    assert "a draft" in plan.prompt, "the material is still pasted, mismatch and all"

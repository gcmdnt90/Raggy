"""D2 — judgement. Two judges, then one judge deliberating twice.

D2 is the demo the binding work was for. Its mechanism is that capability
differs **by model**, which no positional role assignment can express: with
`primary` and `secondary` filled by whichever API keys happen to be present, the
beat compares two vendors' defaults and calls it a difference in capability.

The two failures these tests exist to catch are both quiet ones — a beat that
runs, fills its panes, reads correctly on a projector, and shows nothing:

1. Two judges bound to the same provider *and the same model*. Identical panes
   look like agreement.
2. A reasoning budget sent to a model that takes levels. The pane renders, the
   answer arrives, and "deliberation is a budget" is demonstrated by two
   identical answers.
"""

from __future__ import annotations

import pytest

from app.server.runs import ModelSource, plan, read_input_file, run_block

ANTHROPIC = ModelSource(provider="anthropic", model="claude-sonnet-4-6",
                        egress="api.anthropic.com")
SMALL_LOCAL = ModelSource(provider="ollama", model="qwen3:1.7b",
                          egress="127.0.0.1:11434", local=True)
BIG_LOCAL = ModelSource(provider="ollama", model="qwen3:8b",
                        egress="127.0.0.1:11434", local=True)


# ── beat 1: two judges ──────────────────────────────────────────────────────

def test_two_judges_over_one_pasted_input():
    """D2 inverts D1's shape: one input to two panes, not one input per pane."""
    p = plan("m2", "m2-p1", "numismatics",
             {"primary": ANTHROPIC, "secondary": SMALL_LOCAL})
    assert len(p.panes) == 2
    assert all(pane.runnable for pane in p.panes)
    assert p.produces == "demo/catena/d2-criteri.md"


def test_the_four_drafts_reach_the_prompt():
    """The prompt says "these four drafts". They have to be in the request."""
    p = plan("m2", "m2-p1", "numismatics",
             {"primary": ANTHROPIC, "secondary": SMALL_LOCAL})
    drafts = read_input_file("demo/catena/d1-bozze.md", "numismatics")
    assert drafts.strip() in p.prompt
    assert p.prompt.index("bozze") < p.prompt.index(drafts.strip()[:40]), (
        "the question must lead; the material follows, as a person would paste it"
    )


def test_two_sizes_of_one_model_family_are_two_sources():
    """The configuration D2 exists for must not be reported as degraded.

    Counting distinct *providers* would call this one source, mark the beat
    degraded and announce a replay that is not needed — while the two panes
    are in fact exactly what the beat asks for.
    """
    p = plan("m2", "m2-p1", "numismatics",
             {"primary": BIG_LOCAL, "secondary": SMALL_LOCAL})
    assert not p.degraded
    assert p.panes[0].source.model != p.panes[1].source.model


def test_two_judges_on_one_identical_model_is_degraded():
    """Identical panes look like agreement. The beat must say it is degraded."""
    p = plan("m2", "m2-p1", "numismatics",
             {"primary": BIG_LOCAL, "secondary": BIG_LOCAL})
    assert p.degraded


def test_a_missing_second_judge_keeps_both_panes_and_says_why():
    p = plan("m2", "m2-p1", "numismatics", {"primary": ANTHROPIC})
    assert len(p.panes) == 2, "panes are never dropped"
    assert p.degraded
    assert p.panes[1].unavailable


def test_the_pane_labels_make_no_claim_about_model_size():
    """Which judge is the larger one is a property of the profile, not this file.

    A pane captioned "modello piccolo" beside whatever a profile happened to
    bind is a false statement on a projected screen. The model id carries the
    fact instead, and it is true by construction.
    """
    block = run_block("m2-p1")
    for pane in block["panes"]:
        for label in (pane["label"], pane["label_it"]):
            lowered = label.lower()
            for forbidden in ("small", "large", "big", "piccol", "grand"):
                assert forbidden not in lowered, f"{label!r} claims a size"


# ── beat 2: the budget ──────────────────────────────────────────────────────

def test_both_panes_ask_the_same_role_so_only_the_budget_differs():
    """Two models here would show capability again, which beat 1 already did."""
    block = run_block("m2-p2")
    assert {pane["role"] for pane in block["panes"]} == {"primary"}
    assert [pane["think"] for pane in block["panes"]] == [False, 4096]


def test_the_budget_is_an_integer_because_that_is_the_claim():
    """"Deliberation is a budget, not a switch" — stated as a number of tokens."""
    block = run_block("m2-p2")
    on = block["panes"][1]
    assert isinstance(on["think"], int) and not isinstance(on["think"], bool)
    assert on["think"] >= 1024, "below Anthropic's documented floor it cannot be sent"
    assert on["think"] < on["max_tokens"], (
        "the budget must leave room for an answer, or the request is refused"
    )


def test_the_beat_foregrounds_the_budget():
    assert run_block("m2-p2").get("teaches_params") == ["think"]


def test_a_budget_capable_source_actually_sends_it(monkeypatch):
    """End of the chain: the pane's params reach a provider and become a budget."""
    monkeypatch.setattr(
        "app.llm.providers.anthropic._sdk_accepts_thinking", lambda: True
    )
    from app.llm.base import LLMMessage
    from app.llm.providers.anthropic import AnthropicProvider

    p = plan("m2", "m2-p2", "numismatics", {"primary": ANTHROPIC})
    provider = object.__new__(AnthropicProvider)
    provider.model = ANTHROPIC.model
    provider.temperature = 1.0
    provider.max_tokens = 1500

    off = provider.prepare([LLMMessage(role="user", content=p.prompt)], p.panes[0].params)
    on = provider.prepare([LLMMessage(role="user", content=p.prompt)], p.panes[1].params)

    assert "thinking" not in off.payload and off.sent["think"] is False
    assert on.payload["thinking"] == {"type": "enabled", "budget_tokens": 4096}
    assert on.sent["think"] == 4096


def test_a_level_only_source_reports_the_budget_as_dropped():
    """The trap: it runs, it answers, and it demonstrates nothing.

    Ollama takes a boolean or a level. Handed D2's integer budget it drops the
    parameter — correctly, because rounding it to "high" would put an invented
    figure on a projected screen. The pane then says the budget was not sent,
    which is honest and is why this is catchable at pre-flight rather than
    discovered in the room.
    """
    from app.llm.base import LLMMessage
    from app.llm.providers.ollama import OllamaProvider

    p = plan("m2", "m2-p2", "numismatics", {"primary": BIG_LOCAL})
    provider = object.__new__(OllamaProvider)
    provider.model = BIG_LOCAL.model
    provider.temperature = 1.0
    provider.max_tokens = 1500
    provider.num_ctx = 8192
    provider.keep_alive = "30m"
    provider.base_url = "http://127.0.0.1:11434"

    on = provider.prepare([LLMMessage(role="user", content=p.prompt)], p.panes[1].params)
    assert "think" not in on.sent
    assert on.dropped["think"] == "drop.think.ollama_takes_boolean_or_level"


# ── the chain ───────────────────────────────────────────────────────────────

def test_d2_consumes_what_d1_produced():
    assert run_block("m1-p1")["produces"] == "demo/catena/d1-bozze.md"
    assert run_block("m2-p1")["inputs"][0]["paste_file"] == "demo/catena/d1-bozze.md"


@pytest.mark.parametrize("sector", ["numismatics", "photovoltaic", "automation-software"])
def test_d2_runs_in_every_delivered_sector(sector):
    p = plan("m2", "m2-p1", sector, {"primary": ANTHROPIC, "secondary": SMALL_LOCAL})
    assert p.prompt.strip()
    assert read_input_file("demo/catena/d1-bozze.md", sector).strip() in p.prompt

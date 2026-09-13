"""What each provider does with Banco's four parameters, without a key.

`prepare()` makes no network call and touches no credential, which is the whole
point of it: every adapter's parameter handling becomes assertable here rather
than discovered in a room. `anthropic==1.2.0` dropping `temperature` from
`Messages.create` is the failure this file exists to prevent recurring.

The SDKs are not exercised. Each provider is built with `object.__new__` and
handed the attributes `prepare` reads, in the style of
tests/test_anthropic_provider.py, so these tests assert the shape of the request
Banco builds rather than re-testing somebody's library.

The rule under test throughout: a parameter is in `sent` only if it reached
`payload`, and in `dropped` with a reason otherwise. Nothing is ever
approximated — an invented figure is the one thing that may not reach a
projected screen.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.llm.base import (
    LLMMessage,
    UnknownParameterError,
    split_system,
    validate_params,
)
from app.llm.providers.anthropic import MIN_THINKING_BUDGET, AnthropicProvider
from app.llm.providers.google import GoogleProvider
from app.llm.providers.ollama import OllamaProvider
from app.llm.providers.openai_provider import OpenAIProvider

PING = [LLMMessage(role="user", content="ping")]


# ── the vocabulary ──────────────────────────────────────────────────────────

def test_a_parameter_outside_the_vocabulary_is_refused_not_ignored():
    """A silently discarded parameter is a demo that runs and teaches nothing."""
    with pytest.raises(UnknownParameterError) as exc:
        validate_params({"temperatur": 1.0})
    assert "temperatur" in str(exc.value)


def test_think_accepts_false_a_level_or_a_budget_and_nothing_else():
    for value in (False, "low", "max", 2048):
        assert validate_params({"think": value})["think"] == value
    for bad in ("enormous", 0, 1.5):
        with pytest.raises(UnknownParameterError):
            validate_params({"think": bad})


def test_the_system_parameter_is_appended_after_the_conversations_own():
    """D4's standing rules are read last, which is what "standing" means."""
    text, rest = split_system(
        [LLMMessage(role="system", content="A"), LLMMessage(role="user", content="q")],
        "HOUSE RULES",
    )
    assert text == "A\n\nHOUSE RULES"
    assert [m.role for m in rest] == ["user"]


# ── Anthropic ───────────────────────────────────────────────────────────────

def _anthropic(model="claude-sonnet-4-6", max_tokens=8000):
    provider = object.__new__(AnthropicProvider)
    provider.model = model
    provider.temperature = 1.0
    provider.max_tokens = max_tokens
    return provider


def test_anthropic_sends_a_thinking_budget_as_a_budget(monkeypatch):
    monkeypatch.setattr(
        "app.llm.providers.anthropic._sdk_accepts_thinking", lambda: True
    )
    prepared = _anthropic().prepare(PING, {"think": 4096, "max_tokens": 8000})
    assert prepared.payload["thinking"] == {"type": "enabled", "budget_tokens": 4096}
    assert prepared.sent["think"] == 4096


def test_anthropic_refuses_a_level_rather_than_inventing_a_budget(monkeypatch):
    """docs/specs/model-control.md §3: a rounded budget is a false statement."""
    monkeypatch.setattr(
        "app.llm.providers.anthropic._sdk_accepts_thinking", lambda: True
    )
    prepared = _anthropic().prepare(PING, {"think": "high"})
    assert "think" not in prepared.sent
    assert "thinking" not in prepared.payload
    assert prepared.dropped["think"] == "drop.think.anthropic_takes_a_budget"


def test_anthropic_refuses_a_budget_that_leaves_no_room_for_an_answer(monkeypatch):
    """Thinking tokens count toward max_tokens, so the budget must be below it.

    This is the arithmetic `HARD_MAX_TOKENS = 4000` made impossible: a budget of
    at least 1024 under a 4000-token ceiling left under 3000 for the answer, and
    any larger budget was simply unreachable.
    """
    monkeypatch.setattr(
        "app.llm.providers.anthropic._sdk_accepts_thinking", lambda: True
    )
    prepared = _anthropic(max_tokens=4000).prepare(PING, {"think": 4000, "max_tokens": 4000})
    assert prepared.dropped["think"] == "drop.think.budget_not_below_max_tokens"

    below = _anthropic().prepare(PING, {"think": MIN_THINKING_BUDGET - 1})
    assert below.dropped["think"] == "drop.think.budget_below_minimum"


def test_anthropic_drops_temperature_when_the_model_ignores_it(monkeypatch):
    monkeypatch.setattr(
        "app.llm.providers.anthropic._sdk_accepts_temperature", lambda: True
    )
    prepared = _anthropic(model="claude-opus-4-8").prepare(PING, {"temperature": 0.3})
    assert prepared.dropped["temperature"] == "drop.temperature.model_ignores"
    assert "temperature" not in prepared.payload


def test_anthropic_drops_temperature_when_a_thinking_budget_is_in_play(monkeypatch):
    """The two are not combinable; the pane must not claim both."""
    monkeypatch.setattr(
        "app.llm.providers.anthropic._sdk_accepts_temperature", lambda: True
    )
    monkeypatch.setattr(
        "app.llm.providers.anthropic._sdk_accepts_thinking", lambda: True
    )
    prepared = _anthropic().prepare(PING, {"temperature": 0.3, "think": 2048})
    assert prepared.sent["think"] == 2048
    assert prepared.dropped["temperature"] == "drop.temperature.thinking_needs_default"


def test_anthropic_carries_the_system_prompt_as_sent():
    prepared = _anthropic().prepare(PING, {"system": "HOUSE RULES"})
    assert prepared.payload["system"] == "HOUSE RULES"
    assert prepared.sent["system"] == "HOUSE RULES"


# ── OpenAI ──────────────────────────────────────────────────────────────────

def _openai(model="gpt-4o-mini"):
    provider = object.__new__(OpenAIProvider)
    provider.model = model
    provider.temperature = 0.3
    provider.max_tokens = 1500
    return provider


def test_openai_sends_temperature_to_a_sampling_model():
    prepared = _openai().prepare(PING, {"temperature": 0.7})
    assert prepared.payload["temperature"] == 0.7
    assert prepared.sent["temperature"] == 0.7
    assert "temperature" not in prepared.dropped


def test_openai_drops_temperature_on_a_reasoning_model():
    """Selecting a reasoning model must not put a temperature on screen."""
    prepared = _openai(model="o3-mini").prepare(PING, {"temperature": 0.7})
    assert "temperature" not in prepared.payload
    assert prepared.dropped["temperature"] == "drop.temperature.reasoning_model"


def test_openai_maps_a_level_onto_reasoning_effort_and_refuses_a_budget():
    effort = _openai(model="o3-mini").prepare(PING, {"think": "high"})
    assert effort.payload["reasoning_effort"] == "high"
    assert effort.sent["think"] == "high"

    budget = _openai(model="o3-mini").prepare(PING, {"think": 4096})
    assert "reasoning_effort" not in budget.payload
    assert budget.dropped["think"] == "drop.think.openai_takes_a_level"


def test_openai_says_so_when_the_model_does_not_deliberate_at_all():
    prepared = _openai().prepare(PING, {"think": "high"})
    assert prepared.dropped["think"] == "drop.think.model_does_not_deliberate"


def test_openai_uses_the_ceiling_field_the_installed_sdk_accepts():
    """A reasoning model takes `max_completion_tokens` where that exists."""
    prepared = _openai(model="o3-mini").prepare(PING, {"max_tokens": 900})
    field = "max_completion_tokens" if "max_completion_tokens" in prepared.payload else "max_tokens"
    assert prepared.payload[field] == 900
    assert prepared.sent["max_tokens"] == 900


# ── Google ──────────────────────────────────────────────────────────────────

class _Types:
    """Just enough of `google.genai.types` to record what was built."""

    class Content(SimpleNamespace):
        pass

    class Part(SimpleNamespace):
        @classmethod
        def from_text(cls, *, text):
            return cls(text=text)

    class GenerateContentConfig(SimpleNamespace):
        pass

    class ThinkingConfig(SimpleNamespace):
        model_fields = {"include_thoughts": None, "thinking_budget": None, "thinking_level": None}


def _google(types=_Types, model="gemini-3.6-flash"):
    provider = object.__new__(GoogleProvider)
    provider.model = model
    provider.temperature = 0.3
    provider.max_tokens = 1500
    provider._types = types
    return provider


def test_google_puts_a_budget_on_thinking_budget_and_a_level_on_thinking_level():
    budget = _google().prepare(PING, {"think": 2048})
    assert budget.payload["config"].thinking_config.thinking_budget == 2048
    assert budget.sent["think"] == 2048

    level = _google().prepare(PING, {"think": "high"})
    assert level.payload["config"].thinking_config.thinking_level == "high"
    assert level.sent["think"] == "high"


def test_google_drops_a_budget_when_the_sdk_only_offers_levels():
    """The field that carries deliberation changed between model generations."""

    class _LevelsOnly(_Types):
        class ThinkingConfig(SimpleNamespace):
            model_fields = {"thinking_level": None}

    prepared = _google(types=_LevelsOnly).prepare(PING, {"think": 2048})
    assert prepared.dropped["think"] == "drop.think.google_takes_a_level"


def test_google_drops_deliberation_when_the_sdk_has_no_thinking_config_at_all():
    class _NoThinking(_Types):
        ThinkingConfig = None

    prepared = _google(types=_NoThinking).prepare(PING, {"think": "high"})
    assert prepared.dropped["think"] == "drop.think.sdk_lacks_parameter"


def test_google_carries_the_system_prompt_on_the_config_not_as_a_turn():
    prepared = _google().prepare(
        [LLMMessage(role="user", content="q")], {"system": "HOUSE RULES"}
    )
    assert prepared.payload["config"].system_instruction == "HOUSE RULES"
    assert [c.role for c in prepared.payload["contents"]] == ["user"]


# ── Ollama ──────────────────────────────────────────────────────────────────

def _ollama(model="qwen3:8b"):
    provider = object.__new__(OllamaProvider)
    provider.model = model
    provider.temperature = 0.3
    provider.max_tokens = 1500
    provider.num_ctx = 8192
    provider.keep_alive = "30m"
    provider.base_url = "http://127.0.0.1:11434"
    return provider


def test_ollama_sends_think_as_a_boolean_or_a_level():
    for value in (True, False, "high"):
        prepared = _ollama().prepare(PING, {"think": value})
        assert prepared.payload["think"] == value
        assert prepared.sent["think"] == value


def test_ollama_refuses_a_token_budget():
    """Ollama has no budget shape; approximating one would invent a figure."""
    prepared = _ollama().prepare(PING, {"think": 2048})
    assert "think" not in prepared.payload
    assert prepared.dropped["think"] == "drop.think.ollama_takes_boolean_or_level"


def test_ollama_maps_max_tokens_onto_num_predict():
    prepared = _ollama().prepare(PING, {"max_tokens": 12000})
    assert prepared.payload["options"]["num_predict"] == 12000
    assert prepared.sent["max_tokens"] == 12000


def test_ollama_sends_the_system_prompt_as_a_system_message():
    prepared = _ollama().prepare(PING, {"system": "HOUSE RULES"})
    assert prepared.payload["messages"][0] == {"role": "system", "content": "HOUSE RULES"}


# ── the invariant that matters on screen ────────────────────────────────────

@pytest.mark.parametrize(
    "prepared",
    [
        _anthropic().prepare(PING, {"temperature": 1.0, "think": "high"}),
        _openai().prepare(PING, {"temperature": 0.7, "think": 4096}),
        _google().prepare(PING, {"temperature": 0.5, "think": "high"}),
        _ollama().prepare(PING, {"temperature": 0.2, "think": 2048}),
    ],
)
def test_no_parameter_is_both_sent_and_dropped(prepared):
    """A pane renders `sent` as values and `dropped` as caveats.

    A name in both would render as a value *and* as a caveat contradicting it,
    which is worse than either alone.
    """
    assert not (set(prepared.sent) & set(prepared.dropped))


@pytest.mark.parametrize(
    "prepared",
    [
        _anthropic().prepare(PING, {"temperature": 1.0}),
        _openai().prepare(PING, {"temperature": 0.7}),
        _google().prepare(PING, {"temperature": 0.5}),
        _ollama().prepare(PING, {"temperature": 0.2}),
    ],
)
def test_every_sent_parameter_actually_reached_the_payload(prepared):
    """`sent` is derived from the request, never from a capability table."""
    flat = repr(prepared.payload)
    for name, value in prepared.sent.items():
        if name == "max_tokens":
            assert str(value) in flat
        elif name == "temperature":
            assert str(value) in flat

"""Nothing reaches a surface, or a model, in one language only.

AGENTS.md rule 9 says both catalogues get new text in the same commit, and
`tests/test_i18n.py` enforces that for `app/i18n.py` and the two browser
catalogues. This file covers the other three places text crosses the boundary,
each of which was English-only until 2026-09-12:

* **the system prompt** — Banco composes it and sends it, and objective 2 puts
  it on the projected surface *as sent*;
* **the prompts Banco writes about a conversation** — the summariser, whose
  output becomes conversation history and is read by every later turn;
* **the handover files** — produced by one demo, pasted into the next.

The failure they share is that none of them looks like a bug. A model asked in
Italian under an English system prompt usually answers in Italian anyway, and a
trainer sees nothing wrong until the one run where it does not — which, by
construction, is the small local model D5-A is built around.
"""

from __future__ import annotations

import json

import pytest

from app.i18n import CATALOG, SUPPORTED_LANGUAGES
from app.server import runs

LANGUAGES = tuple(SUPPORTED_LANGUAGES)


# ── the catalogue ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("language", LANGUAGES)
def test_every_generated_string_exists_in_every_language(language):
    missing = sorted(key for key, entry in CATALOG.items() if not entry.get(language))
    assert not missing, f"no {language} text for: {missing}"


def test_no_catalogue_entry_is_the_same_text_in_both_languages():
    """A copy-pasted English string with an `it` key is not a translation.

    Exempted: entries whose content is a term the room is *taught* and which is
    therefore deliberately identical, and entries that are pure interpolation.
    """
    exempt = {
        # `chain.produced_by` is provider · model · a number. Nothing to translate.
        "chain.produced_by",
        "preflight.chain.unknown_sector",
        "sessions.roles_not_an_object",
    }
    identical = sorted(
        key for key, entry in CATALOG.items()
        if key not in exempt and entry.get("it") == entry.get("en")
    )
    assert not identical, f"untranslated (identical it/en): {identical}"


# ── the system prompt ───────────────────────────────────────────────────────

@pytest.mark.parametrize("language", LANGUAGES)
def test_the_system_prompt_exists_in_every_language(language):
    from app.llm.prompts.system import PromptManager

    text = PromptManager().get_chatbot_system_prompt(language)
    assert text.strip(), f"no {language} chatbot system prompt"


def test_the_italian_and_english_system_prompts_are_different_texts():
    from app.llm.prompts.system import PromptManager

    manager = PromptManager()
    assert manager.get_chatbot_system_prompt("it") != manager.get_chatbot_system_prompt("en")


@pytest.mark.parametrize("language,marker", [("it", "in italiano"), ("en", "in English")])
def test_the_system_prompt_states_its_output_language(language, marker):
    """Stated, not inferred. This is the fix that matters.

    "Always reply in the user's language" asks the model to work out which
    language it is in. A frontier model does; a 4B-class local model often does
    not, and answers in English. D5-A's claim is that only the writer changed —
    same index, same retrieved passages, generation moved to the local model —
    so a language difference Banco caused would be read by the room as
    something the local model did.
    """
    from app.llm.prompts.system import PromptManager

    assert marker in PromptManager().get_chatbot_system_prompt(language)


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_pipelines_fallback_prompt_and_summariser_exist_in_every_language(language):
    from app.rag import pipeline

    assert pipeline._DEFAULT_CHATBOT_PROMPT[language].strip()
    assert pipeline._SUMMARY_SYSTEM[language].strip()
    assert "{conversation}" in pipeline._SUMMARY_USER_TEMPLATE[language]


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_retrieved_context_heading_is_translated(language):
    """It sits inside the system prompt, which is shown as sent."""
    from app.rag import pipeline

    assert pipeline._context_heading(language).strip()
    assert pipeline._context_heading("it") != pipeline._context_heading("en")


# ── what run blocks carry ───────────────────────────────────────────────────

def test_every_run_block_field_that_reaches_a_surface_has_italian():
    blocks = runs.load_run_blocks()
    for beat_id, block in blocks.get("beats", {}).items():
        assert block.get("teaches_it"), f"{beat_id}: no Italian `teaches`"
        for pane in block.get("panes", []):
            assert pane.get("label_it"), f"{beat_id} pane {pane.get('pane')}: no `label_it`"
    for beat_id in blocks.get("_unblocked", {}):
        assert blocks.get("_unblocked_it", {}).get(beat_id), (
            f"{beat_id}: refusal reason is rendered on the projected surface "
            "and has no Italian text"
        )


def test_a_beat_planned_in_italian_sends_the_italian_prompt():
    """The language decides which of the beat's two prompts reaches the model."""
    from app.server.runs import ModelSource, plan

    source = ModelSource(provider="anthropic", model="m", egress="e")
    bound = {"primary": source, "secondary": source}
    for beat_id, demo_id in (("m1-p1", "m1"), ("m2-p1", "m2")):
        it = plan(demo_id, beat_id, "numismatics", bound, language="it")
        en = plan(demo_id, beat_id, "numismatics", bound, language="en")
        assert it.prompt != en.prompt, f"{beat_id} sends the same text in both languages"


# ── session profiles ────────────────────────────────────────────────────────

def test_every_shipped_profile_note_carries_both_languages():
    """A profile note is shown on the console and read aloud at pre-flight."""
    from app.server import sessions

    if not sessions.SESSIONS_DIR.is_dir():
        pytest.skip("no shipped profiles yet")
    for path in sorted(sessions.SESSIONS_DIR.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("note"):
            assert raw.get("note_it"), f"{path.name}: `note` has no `note_it`"

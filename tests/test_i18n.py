"""Banco speaks two languages, and neither may leak into the other.

Three failure modes are checked here, all of which would surface in a room:

* a key present in one catalogue and missing from the other — the room reads a
  raw key like ``harness.run`` off a projected screen;
* a placeholder that exists in one language and not the other — the label loses
  the value it was supposed to carry;
* language held as process state — the trainer switches the console to English
  and the projector, mid-lesson, follows.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app import i18n
from app.server import demos, runs
from app.server.runs import ModelSource

WEB = Path(__file__).resolve().parent.parent / "app" / "web" / "shared"
PLACEHOLDER = re.compile(r"\{(\w+)\}")

API_A = ModelSource(provider="anthropic", model="claude-x", egress="api.anthropic.com")
API_B = ModelSource(provider="openai", model="gpt-x", egress="api.openai.com")
CLASSROOM = {"primary": API_A, "secondary": API_B}


# ── the defaults ────────────────────────────────────────────────────────────

def test_banco_speaks_italian_unless_told_otherwise():
    assert i18n.DEFAULT_LANGUAGE == "it"
    assert set(i18n.SUPPORTED_LANGUAGES) == {"it", "en"}


@pytest.mark.parametrize(
    "given", [None, "", "it", "IT", "it-IT", "it_IT", "klingon", "fr", 7]
)
def test_normalize_never_raises_and_never_invents_a_language(given):
    assert i18n.normalize(given) in i18n.SUPPORTED_LANGUAGES


def test_an_unknown_language_becomes_italian_not_english():
    assert i18n.normalize("fr") == "it"
    assert i18n.normalize(None) == "it"


# ── the server catalogue ────────────────────────────────────────────────────

def test_every_server_string_exists_in_both_languages():
    incomplete = sorted(
        key for key, entry in i18n.CATALOG.items()
        if not entry.get("it") or not entry.get("en")
    )
    assert not incomplete, f"server strings missing a language: {incomplete}"


def test_both_languages_carry_the_same_placeholders():
    """A dropped `{model}` is a label that silently stops naming the model."""
    for key, entry in i18n.CATALOG.items():
        it = set(PLACEHOLDER.findall(entry["it"]))
        en = set(PLACEHOLDER.findall(entry["en"]))
        assert it == en, f"{key}: placeholders differ, it={sorted(it)} en={sorted(en)}"


def test_a_missing_key_shows_itself_rather_than_nothing():
    assert i18n.t("no.such.key") == "no.such.key"


def test_formatting_a_string_with_a_missing_value_does_not_raise():
    """A bad call must cost a wrong label, never a failed pre-flight."""
    assert i18n.t("preflight.recordings.ok", "it")  # no `count` supplied


# ── the browser catalogues ──────────────────────────────────────────────────

def _js_catalogue(name: str) -> dict[str, str]:
    """Read one of the strings.*.js files without running JavaScript.

    The files are data with a one-line assignment around them, so the object
    literal is extracted and read as JSON5-ish text. This is a test, not a
    parser: if the shape of those files ever changes, this fails loudly rather
    than silently checking nothing.
    """
    source = (WEB / name).read_text(encoding="utf-8")
    # The catalogue is the last assignment in the file; the line above it is
    # `window.BancoStrings = window.BancoStrings || {}`, whose `{}` must not be
    # mistaken for the start of the object.
    start = source.index("{", source.index("window.BancoStrings."))
    body = source[start: source.rindex("}") + 1]
    # `"a" + "b"` line continuations, then trailing commas, then comments.
    body = re.sub(r'"\s*\+\s*\n?\s*"', "", body)
    body = re.sub(r"//[^\n]*", "", body)
    body = re.sub(r",(\s*[}\]])", r"\1", body)
    return json.loads(body)


def test_the_browser_catalogues_hold_the_same_keys():
    italian = _js_catalogue("strings.it.js")
    english = _js_catalogue("strings.en.js")
    assert italian, "the Italian catalogue is empty — the parser above is wrong"
    assert set(italian) == set(english), (
        f"only in it: {sorted(set(italian) - set(english))}; "
        f"only in en: {sorted(set(english) - set(italian))}"
    )


def test_the_browser_catalogues_carry_the_same_placeholders():
    italian = _js_catalogue("strings.it.js")
    english = _js_catalogue("strings.en.js")
    for key in italian:
        assert set(PLACEHOLDER.findall(italian[key])) == \
               set(PLACEHOLDER.findall(english[key])), f"{key}: placeholders differ"


def test_every_surface_loads_the_language_files_and_offers_the_switch():
    """Both surfaces, not only the console: AGENTS.md section 7 was asked."""
    web = WEB.parent
    for page in (web / "harness" / "index.html", web / "console" / "index.html"):
        html = page.read_text(encoding="utf-8")
        assert "/static/shared/strings.it.js" in html
        assert "/static/shared/strings.en.js" in html
        assert "/static/shared/i18n.js" in html
        assert "data-lang-select" in html, f"{page.name} has no language switch"


# ── the demo material ───────────────────────────────────────────────────────

def test_the_demo_database_is_translated_where_the_room_reads_it():
    """Every demo title, shape and beat label has an Italian form.

    The database is vendored from the deck and is not Banco's to edit, so this
    is a check on the pin rather than a repair: if a new pin arrives with an
    untranslated label, the room finds out here and not on a projector.
    """
    untranslated = []
    for demo in demos.load().get("demos", []):
        for field in ("title", "shape"):
            if not demo.get(f"{field}_it"):
                untranslated.append(f"{demo.get('id')}.{field}")
        for beat in demo.get("prompts", []):
            if not beat.get("label_it"):
                untranslated.append(f"{beat.get('id')}.label")
    assert not untranslated, f"demo database missing Italian: {untranslated}"


def test_every_beat_has_an_italian_prompt():
    """Either on the beat or on each of its sector variants."""
    missing = []
    for demo in demos.load().get("demos", []):
        for beat in demo.get("prompts", []):
            variants = beat.get("variants") or {}
            if variants:
                for sector, variant in variants.items():
                    if not variant.get("text_it"):
                        missing.append(f"{beat.get('id')}/{sector}")
            elif beat.get("text") and not beat.get("text_it"):
                missing.append(beat.get("id"))
    assert not missing, f"beats with no Italian prompt: {missing}"


def test_every_pasted_input_matches_the_prompt_in_both_languages():
    """A placeholder is written in the prompt's language, so it is translated.

    This is the check that caught `[PASTE RAW NOTES]` being substituted into an
    Italian prompt that says `[INCOLLA APPUNTI GREZZI]`: the beat ran, the room
    saw a prompt, and the pasted file was simply not in it.
    """
    for beat_id, block in runs.load_run_blocks()["beats"].items():
        for spec in block.get("inputs", []):
            if not spec.get("replaces"):
                continue
            demo_id = beat_id.split("-")[0]
            for language in ("it", "en"):
                beat = runs.find_beat(demo_id, beat_id, "numismatics")
                raw = i18n.localized(beat, "text", language, default="")
                placeholder = i18n.localized(spec, "replaces", language)
                assert placeholder in raw, (
                    f"{beat_id}: {placeholder!r} is not in the {language} prompt"
                )
                built = runs.build_prompt(beat, block, "numismatics", language=language)
                assert placeholder not in built, (
                    f"{beat_id}: the {language} prompt still carries its placeholder"
                )


def test_every_appended_input_reaches_the_prompt_in_both_languages():
    """An input with no placeholder is appended, and must actually arrive.

    D2's two beats name `demo/catena/d1-bozze.md` and have no `[PASTE …]` hole:
    the prompt says "these four drafts" and expects them to be in the
    conversation, because in the room a person pastes them under the question.
    Appending is the same gesture — and it fails the same silent way if it does
    not happen, with a model asked to compare four drafts it was never given.
    """
    for beat_id, block in runs.load_run_blocks()["beats"].items():
        for spec in block.get("inputs", []):
            if not spec.get("append"):
                continue
            demo_id = beat_id.split("-")[0]
            for language in ("it", "en"):
                beat = runs.find_beat(demo_id, beat_id, "numismatics")
                raw = i18n.localized(beat, "text", language, default="")
                built = runs.build_prompt(beat, block, "numismatics", language=language)
                content = runs.read_input_file(spec["paste_file"], "numismatics")
                assert built.startswith(raw.rstrip()), (
                    f"{beat_id}: the {language} prompt no longer leads the request"
                )
                assert content.strip() in built, (
                    f"{beat_id}: {spec['paste_file']} did not reach the {language} prompt"
                )


def test_no_input_is_both_substituted_and_appended():
    """Two ways to place the same file would place it twice."""
    for beat_id, block in runs.load_run_blocks()["beats"].items():
        for spec in block.get("inputs", []):
            assert not (spec.get("append") and spec.get("replaces")), (
                f"{beat_id} declares an input that both substitutes and appends"
            )


def test_run_blocks_are_translated():
    blocks = runs.load_run_blocks()
    for beat_id, block in blocks["beats"].items():
        assert block.get("teaches_it"), f"{beat_id} has no Italian `teaches`"
        for pane in block.get("panes", []):
            assert pane.get("label_it"), f"{beat_id} pane {pane.get('pane')} has no label_it"
    assert set(blocks["_unblocked"]) == set(blocks["_unblocked_it"]), (
        "the two refusal-reason maps disagree"
    )


# ── the language is per call, not per process ───────────────────────────────

def test_planning_in_two_languages_sends_two_different_prompts():
    italian = runs.plan("m1", "m1-p1", "numismatics", CLASSROOM, language="it")
    english = runs.plan("m1", "m1-p1", "numismatics", CLASSROOM, language="en")
    assert italian.prompt != english.prompt
    assert italian.language == "it" and english.language == "en"


def test_pane_labels_follow_the_language_of_the_run():
    italian = runs.plan("m1", "m1-p1", "numismatics", CLASSROOM, language="it")
    english = runs.plan("m1", "m1-p1", "numismatics", CLASSROOM, language="en")
    assert [p.label for p in italian.panes] != [p.label for p in english.panes]


def test_planning_in_english_does_not_change_the_next_italian_plan():
    """The regression the module docstring warns about, as a test."""
    first = runs.plan("m1", "m1-p1", "numismatics", CLASSROOM, language="it")
    runs.plan("m1", "m1-p1", "numismatics", CLASSROOM, language="en")
    again = runs.plan("m1", "m1-p1", "numismatics", CLASSROOM, language="it")
    assert first.prompt == again.prompt
    assert [p.label for p in first.panes] == [p.label for p in again.panes]


def test_a_beat_with_no_italian_prompt_falls_back_rather_than_going_blank():
    """Falling back to English is a compromise; an empty prompt is a failure."""
    beat = {"text": "only english here"}
    assert runs.build_prompt(beat, {}, "numismatics", language="it") == "only english here"


def test_the_i18n_module_holds_no_language_state():
    """`set_language` and `_ui_language` are gone on purpose. Keep them gone."""
    assert not hasattr(i18n, "set_language")
    assert not hasattr(i18n, "get_language")
    assert not hasattr(i18n, "_ui_language")

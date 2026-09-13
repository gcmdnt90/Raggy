"""Credentials must not survive the trip to a screen or a log file.

SECURITY.md promises participant keys are "redacted from logs, and never
rendered by the harness". These are the tests that make that a property of the
code rather than of nobody having triggered the right provider error yet.
"""

from __future__ import annotations

import logging

import pytest

from app.utils.redact import PLACEHOLDER, RedactingFilter, redact, secret_values

GOOGLE_KEY = "AQ.Ab8RN6J" + "x" * 40
OPENAI_KEY = "sk-proj-" + "a" * 60
ANTHROPIC_KEY = "sk-ant-api03-" + "b" * 80


# ── the shapes that actually reach us ───────────────────────────────────────

def test_a_key_in_a_url_query_is_removed():
    """How google-genai authenticates, so this is the one that fires."""
    text = f"GET https://generativelanguage.googleapis.com/v1beta/models?key={GOOGLE_KEY} failed"
    out = redact(text)
    assert GOOGLE_KEY not in out
    assert PLACEHOLDER in out
    # The host survives: PROJECT.md invariant 4 puts the egress target on screen.
    assert "generativelanguage.googleapis.com" in out


def test_a_masked_openai_fragment_is_still_removed():
    """OpenAI's 401 echoes the key it rejected, partly masked.

    A fragment on a screen that has been projected is still a fragment of a
    real key — app/server/preflight.py says the same about pre-flight.
    """
    out = redact("Incorrect API key provided: sk-proj-abcd************************wxyz.")
    assert "sk-proj-abcd" not in out
    assert PLACEHOLDER in out


@pytest.mark.parametrize(
    "text",
    [
        f"x-goog-api-key: {GOOGLE_KEY}",
        f"Authorization: Bearer {OPENAI_KEY}",
        f'{{"x-api-key": "{ANTHROPIC_KEY}"}}',
        f"connection failed with token={OPENAI_KEY}",
    ],
)
def test_header_and_token_forms_are_removed(text):
    out = redact(text)
    assert GOOGLE_KEY not in out
    assert OPENAI_KEY not in out
    assert ANTHROPIC_KEY not in out
    assert PLACEHOLDER in out


def test_an_exact_configured_value_is_removed_whatever_its_shape():
    """The backstop for a key an SDK embeds in a shape no pattern anticipated."""
    weird = "not-a-recognisable-key-shape-at-all"
    assert weird not in redact(f"refused: {weird}", weird)


def test_a_short_value_is_not_treated_as_a_secret():
    """Otherwise an ordinary word in the message would be redacted away."""
    assert redact("model gpt-5 refused", "gpt-5") == "model gpt-5 refused"


def test_the_message_still_says_what_went_wrong():
    out = redact(f"LLMAuthenticationError: 401 UNAUTHENTICATED. key={GOOGLE_KEY}")
    assert "LLMAuthenticationError" in out
    assert "401 UNAUTHENTICATED" in out


def test_an_exception_can_be_passed_directly():
    assert redact(ValueError(f"bad key {OPENAI_KEY}")) == f"bad key {PLACEHOLDER}"


# ── which values count as secrets ───────────────────────────────────────────

def test_secret_values_takes_the_key_and_leaves_the_egress_host():
    """`provider_kwargs` returns api_key for an API provider, base_url for Ollama.

    Redacting the base URL would blank the egress target out of exactly the
    error where a trainer needs to read it.
    """
    assert secret_values({"api_key": ANTHROPIC_KEY}) == (ANTHROPIC_KEY,)
    assert secret_values({"base_url": "http://localhost:11434"}) == ()
    assert secret_values(None) == ()


# ── the logging filter ──────────────────────────────────────────────────────

def _record(msg, args=(), exc_info=None):
    return logging.LogRecord("raggy.test", logging.ERROR, __file__, 1, msg, args, exc_info)


def test_the_log_filter_scrubs_the_message():
    record = _record("calling with key=%s", (GOOGLE_KEY,))
    RedactingFilter().filter(record)
    assert GOOGLE_KEY not in record.getMessage()


def test_the_log_filter_scrubs_a_traceback():
    """`logger.exception` in the runner is how a key would reach raggy.log."""
    try:
        raise RuntimeError(f"transport error for ?key={GOOGLE_KEY}")
    except RuntimeError:
        import sys

        record = _record("Pane %s crashed", (0,), exc_info=sys.exc_info())

    RedactingFilter().filter(record)
    assert record.exc_text is not None
    assert GOOGLE_KEY not in record.exc_text
    # A formatter reuses exc_text when it is set, so the raw exception is never
    # rendered downstream.
    assert PLACEHOLDER in record.exc_text

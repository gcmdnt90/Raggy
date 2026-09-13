"""Regression tests for the Google provider.

There was no test here, which is how `app/llm/providers/google.py` came to
import `google.generativeai` while `pyproject.toml` and both locks pin
`google-genai`. A configured Google key produced a dead pane and the suite had
nothing to say about it.

The SDK is not imported. Like tests/test_anthropic_provider.py, the provider is
built with `object.__new__` and handed a request-capturing client, so these
tests assert the shape of the call Banco makes rather than re-testing Google's
library.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.llm.base import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMMessage,
    LLMModelNotFoundError,
    LLMRateLimitError,
)
from app.llm.providers.google import GoogleProvider


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


def _provider(model: str = "gemini-2.5-flash", temperature: float = 0.3) -> GoogleProvider:
    provider = object.__new__(GoogleProvider)
    provider.api_key = "AQ.test-key"
    provider.model = model
    provider.temperature = temperature
    provider.max_tokens = 1500
    provider._types = _Types
    provider._client = MagicMock()
    return provider


def _response(text="pong"):
    return SimpleNamespace(
        text=text,
        usage_metadata=SimpleNamespace(
            prompt_token_count=3, candidates_token_count=1, total_token_count=4
        ),
    )


# ── the call Banco makes ────────────────────────────────────────────────────

def test_generate_uses_the_genai_client_api():
    """The client-based API, not the model-object API of the previous SDK."""
    provider = _provider()
    provider._client.models.generate_content.return_value = _response()

    result = provider.generate([LLMMessage(role="user", content="ping")])

    kwargs = provider._client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-2.5-flash"
    assert result.content == "pong"
    assert result.provider == "google"
    assert result.usage == {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4}


def test_the_system_prompt_travels_on_the_config_not_as_a_turn():
    """Gemini has no system role; it takes a system_instruction."""
    provider = _provider()
    provider._client.models.generate_content.return_value = _response()

    provider.generate([
        LLMMessage(role="system", content="be terse"),
        LLMMessage(role="user", content="ping"),
    ])

    kwargs = provider._client.models.generate_content.call_args.kwargs
    assert kwargs["config"].system_instruction == "be terse"
    assert [c.role for c in kwargs["contents"]] == ["user"]


def test_assistant_turns_are_sent_as_the_model_role():
    """`continues` beats replay the pane's own earlier answer, so this matters."""
    provider = _provider()
    provider._client.models.generate_content.return_value = _response()

    provider.generate([
        LLMMessage(role="user", content="first"),
        LLMMessage(role="assistant", content="answer"),
        LLMMessage(role="user", content="where did that come from?"),
    ])

    contents = provider._client.models.generate_content.call_args.kwargs["contents"]
    assert [c.role for c in contents] == ["user", "model", "user"]


def test_sampling_parameters_are_passed_through():
    provider = _provider(temperature=0.25)
    provider._client.models.generate_content.return_value = _response()

    provider.generate([LLMMessage(role="user", content="ping")], max_tokens=64)

    config = provider._client.models.generate_content.call_args.kwargs["config"]
    assert config.temperature == 0.25
    assert config.max_output_tokens == 64


def test_generate_stream_yields_chunk_text():
    provider = _provider()
    provider._client.models.generate_content_stream.return_value = iter([
        SimpleNamespace(text="po"), SimpleNamespace(text=None), SimpleNamespace(text="ng"),
    ])

    assert list(provider.generate_stream([LLMMessage(role="user", content="ping")])) == ["po", "ng"]


def test_available_models_strips_the_models_prefix_and_filters_by_action():
    provider = _provider()
    provider._client.models.list.return_value = [
        SimpleNamespace(name="models/gemini-2.5-flash", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/text-embedding-004", supported_actions=["embedContent"]),
        SimpleNamespace(name="models/gemini-2.5-pro", supported_actions=["generateContent"]),
    ]

    assert provider._fetch_models() == ["gemini-2.5-flash", "gemini-2.5-pro"]


def test_embed_returns_plain_float_lists():
    provider = _provider()
    provider._client.models.embed_content.return_value = SimpleNamespace(
        embeddings=[SimpleNamespace(values=[0.1, 0.2]), SimpleNamespace(values=[0.3])]
    )

    assert provider.embed(["a", "b"]) == [[0.1, 0.2], [0.3]]


# ── error classification ────────────────────────────────────────────────────

class _APIError(Exception):
    """Stands in for google.genai.errors.APIError, which carries code+status."""

    def __init__(self, code, status, message="refused"):
        self.code = code
        self.status = status
        super().__init__(f"{code} {status}. {message}")


@pytest.mark.parametrize(
    ("code", "status", "expected"),
    [
        (401, "UNAUTHENTICATED", LLMAuthenticationError),
        (403, "PERMISSION_DENIED", LLMAuthenticationError),
        (404, "NOT_FOUND", LLMModelNotFoundError),
        (429, "RESOURCE_EXHAUSTED", LLMRateLimitError),
        (500, "INTERNAL", LLMConnectionError),
    ],
)
def test_api_errors_map_onto_bancos_exception_family(code, status, expected):
    """Classified by status code first: `str(exc)` is the raw response body."""
    provider = _provider()
    provider._client.models.generate_content.side_effect = _APIError(code, status)

    with pytest.raises(expected):
        provider.generate([LLMMessage(role="user", content="ping")])


def test_an_expected_connection_failure_logs_no_traceback_and_no_message(caplog):
    """The SDK's message can carry the key, so only the exception type is logged."""
    provider = _provider()
    provider.generate = MagicMock(side_effect=LLMAuthenticationError("?key=AQ.secret-value"))

    with caplog.at_level(logging.WARNING, logger="app.llm.providers.google"):
        assert provider.test_connection() is False

    assert len(caplog.records) == 1
    assert "AQ.secret-value" not in caplog.records[0].getMessage()
    assert caplog.records[0].exc_info is None

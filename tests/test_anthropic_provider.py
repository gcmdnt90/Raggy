"""Regression tests for Anthropic provider behaviour."""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.llm.base import LLMAuthenticationError, LLMMessage
from app.llm.providers.anthropic import AnthropicProvider


def _provider(model: str, temperature: float = 0.3) -> AnthropicProvider:
    """Build a provider with a request-capturing client and no network calls."""
    provider = object.__new__(AnthropicProvider)
    provider.model = model
    provider.temperature = temperature
    provider.max_tokens = 1500
    provider._client = MagicMock()
    return provider


@pytest.mark.parametrize(
    "model",
    [
        "claude-opus-4-7",
        "claude-opus-4-8",
        "claude-sonnet-5",
        "claude-fable-5",
        "claude-mythos-5",
    ],
)
def test_generate_omits_temperature_for_new_models(model):
    provider = _provider(model)
    provider._client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text="pong")],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        model=model,
    )

    provider.generate([LLMMessage(role="user", content="ping")])

    assert "temperature" not in provider._client.messages.create.call_args.kwargs


@pytest.mark.parametrize(
    "model",
    [
        "claude-sonnet-4-6",
        "claude-opus-4-6",
        "claude-3-5-sonnet-20241022",
    ],
)
def test_generate_preserves_temperature_for_compatible_models(model):
    provider = _provider(model, temperature=0.25)
    provider._client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text="pong")],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        model=provider.model,
    )

    provider.generate([LLMMessage(role="user", content="ping")])

    assert provider._client.messages.create.call_args.kwargs["temperature"] == 0.25


def test_generate_stream_omits_temperature_for_new_models():
    provider = _provider("claude-sonnet-5")
    stream = MagicMock()
    stream.__enter__.return_value.text_stream = iter(["po", "ng"])
    provider._client.messages.stream.return_value = stream

    assert list(provider.generate_stream([LLMMessage(role="user", content="ping")])) == [
        "po",
        "ng",
    ]
    assert "temperature" not in provider._client.messages.stream.call_args.kwargs


def test_expected_connection_failure_logs_no_traceback(caplog):
    provider = _provider("claude-sonnet-4-6")
    provider.generate = MagicMock(side_effect=LLMAuthenticationError("invalid key"))

    with caplog.at_level(logging.WARNING, logger="app.llm.providers.anthropic"):
        assert provider.test_connection() is False

    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert caplog.records[0].exc_info is None

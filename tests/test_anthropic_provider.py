"""Regression tests for Anthropic provider behaviour."""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.llm.base import LLMAuthenticationError, LLMMessage
from app.llm.providers import anthropic as anthropic_provider
from app.llm.providers.anthropic import AnthropicProvider, temperature_is_applied


@pytest.fixture
def sdk_carries_temperature(monkeypatch):
    """Pretend the installed SDK still has the parameter.

    The model rule and the SDK rule are separate gates and have to be tested
    separately — `anthropic==1.2.0` closed the SDK gate for every model, which
    would otherwise make the model-rule tests below pass for the wrong reason.
    """
    monkeypatch.setattr(anthropic_provider, "_sdk_accepts_temperature", lambda: True)


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
def test_generate_omits_temperature_for_new_models(model, sdk_carries_temperature):
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
def test_generate_preserves_temperature_for_compatible_models(model, sdk_carries_temperature):
    provider = _provider(model, temperature=0.25)
    provider._client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text="pong")],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        model=provider.model,
    )

    provider.generate([LLMMessage(role="user", content="ping")])

    assert provider._client.messages.create.call_args.kwargs["temperature"] == 0.25


def test_generate_stream_omits_temperature_for_new_models(sdk_carries_temperature):
    provider = _provider("claude-sonnet-5")
    stream = MagicMock()
    stream.__enter__.return_value.text_stream = iter(["po", "ng"])
    provider._client.messages.stream.return_value = stream

    assert list(provider.generate_stream([LLMMessage(role="user", content="ping")])) == [
        "po",
        "ng",
    ]
    assert "temperature" not in provider._client.messages.stream.call_args.kwargs


def test_no_temperature_is_sent_when_the_sdk_has_no_field_for_it(monkeypatch):
    """The regression that killed every Anthropic pane.

    `anthropic==1.2.0`'s `Messages.create` has no `temperature` parameter and
    no `**kwargs`, so sending one raised TypeError before the request was made.
    The gate is the SDK's, not the model's, so it must close for a model the
    model rule would otherwise allow.
    """
    monkeypatch.setattr(anthropic_provider, "_sdk_accepts_temperature", lambda: False)
    provider = _provider("claude-sonnet-4-6", temperature=0.25)
    provider._client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text="pong")],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        model=provider.model,
    )

    provider.generate([LLMMessage(role="user", content="ping")])

    assert "temperature" not in provider._client.messages.create.call_args.kwargs


def test_the_installed_sdk_decides_and_an_unreadable_one_means_no(monkeypatch):
    """Inspection that fails must resolve to "do not send it".

    Not sending the parameter costs a default temperature; sending one the SDK
    cannot take costs the whole call, and with it the pane.
    """
    anthropic_provider._sdk_accepts_temperature.cache_clear()
    monkeypatch.setattr(
        anthropic_provider.inspect, "signature",
        MagicMock(side_effect=RuntimeError("no signature")),
    )
    assert anthropic_provider._sdk_accepts_temperature() is False
    anthropic_provider._sdk_accepts_temperature.cache_clear()


def test_the_harness_is_told_whenever_no_temperature_travels(monkeypatch):
    """What the projected surface displays must match what was sent.

    PROJECT.md invariant 2 puts the mechanism *as sent* on screen, so
    "temperature 0.3" beside a call that carried none is a false statement in
    front of a room.
    """
    from app.server.sources import temperature_applies

    monkeypatch.setattr(anthropic_provider, "_sdk_accepts_temperature", lambda: False)
    assert temperature_is_applied("claude-sonnet-4-6") is False
    assert temperature_applies("anthropic", "claude-sonnet-4-6") is False
    # A provider with no such rule is unaffected.
    assert temperature_applies("openai", "gpt-4o-mini") is True


def test_expected_connection_failure_logs_no_traceback(caplog):
    provider = _provider("claude-sonnet-4-6")
    provider.generate = MagicMock(side_effect=LLMAuthenticationError("invalid key"))

    with caplog.at_level(logging.WARNING, logger="app.llm.providers.anthropic"):
        assert provider.test_connection() is False

    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert caplog.records[0].exc_info is None

"""Tests for the Raggy LLM router."""

from unittest.mock import MagicMock, patch

import pytest

from app.llm.base import LLMMessage, LLMResponse
from app.llm.router import LLMRouter


class TestLLMRouter:
    """Test LLM router functionality."""

    def test_list_providers(self):
        providers = LLMRouter.list_providers()
        assert "ollama" in providers
        assert "anthropic" in providers
        assert "openai" in providers
        assert "google" in providers

    @patch("app.llm.providers.ollama.OllamaProvider")
    def test_create_ollama_router(self, mock_ollama):
        mock_instance = MagicMock()
        mock_ollama.return_value = mock_instance

        router = LLMRouter("ollama", base_url="http://localhost:11434")
        assert router.provider_name == "ollama"

    def test_invalid_provider_raises(self):
        with pytest.raises(Exception):
            LLMRouter("invalid_provider")

    def test_a_large_max_tokens_is_no_longer_clamped(self):
        """ADR 0005: the ceiling is removed, not raised.

        `HARD_MAX_TOKENS = 4000` silently shortened every long answer and made
        an Anthropic thinking budget impossible to satisfy. The floor stays,
        because zero is not a request.
        """
        assert LLMRouter._effective_max_tokens(None) == 1500
        assert LLMRouter._effective_max_tokens(64000) == 64000
        assert LLMRouter._effective_max_tokens(0) == 1

    def test_a_spent_daily_budget_no_longer_refuses_a_call(self, monkeypatch):
        """The budget is measured and displayed; it does not forbid.

        It refused on a character-count *estimate*, so a demonstration could
        stop mid-lesson for a number nobody in the room could see and that was
        not the true one. Usage is still recorded on every call.
        """
        from app.llm import router as router_module

        assert not hasattr(router_module, "HARD_MAX_TOKENS")
        assert not hasattr(LLMRouter, "_ensure_budget")

    def test_usage_is_still_recorded_on_every_call(self, monkeypatch):
        recorded: list[int] = []
        monkeypatch.setattr("app.llm.router.record_usage", recorded.append)

        provider = MagicMock()
        provider.generate.return_value = LLMResponse(
            content="pong", model="m", provider="stub",
            usage={"total_tokens": 42},
        )
        router = LLMRouter.__new__(LLMRouter)
        router._provider = provider
        router._provider_name = "stub"
        router.generate([LLMMessage(role="user", content="ping")])
        assert recorded == [42]

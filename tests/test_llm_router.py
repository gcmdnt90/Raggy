"""Tests for the Raggy LLM router."""

import pytest
from unittest.mock import MagicMock, patch

from app.llm.base import LLMBudgetExceededError, LLMMessage, LLMResponse
from app.llm.router import HARD_MAX_TOKENS, LLMRouter


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

    def test_effective_max_tokens_is_capped(self):
        assert LLMRouter._effective_max_tokens(None) == 1500
        assert LLMRouter._effective_max_tokens(999999) == HARD_MAX_TOKENS

    def test_budget_guard_raises_when_exhausted(self, monkeypatch):
        monkeypatch.setattr("app.llm.router.can_spend", lambda planned: False)
        with pytest.raises(LLMBudgetExceededError):
            LLMRouter._ensure_budget([LLMMessage(role="user", content="hello")], 100)

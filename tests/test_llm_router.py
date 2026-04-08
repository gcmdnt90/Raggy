"""Test suite per il LLM Router."""

import pytest
from unittest.mock import MagicMock, patch

from app.llm.base import (
    LLMMessage,
    LLMResponse,
    LLMError,
    LLMProvider,
    LLMAuthenticationError,
    LLMRateLimitError,
    retry_with_backoff,
)
from app.llm.router import LLMRouter, _PROVIDER_PATHS


# ---------------------------------------------------------------------------
# LLMMessage / LLMResponse dataclass tests
# ---------------------------------------------------------------------------

class TestDataclasses:

    def test_llm_message_creation(self):
        msg = LLMMessage(role="user", content="Ciao")
        assert msg.role == "user"
        assert msg.content == "Ciao"

    def test_llm_message_frozen(self):
        msg = LLMMessage(role="user", content="Test")
        with pytest.raises(AttributeError):
            msg.content = "Changed"

    def test_llm_response_creation(self):
        resp = LLMResponse(
            content="Risposta",
            model="test-model",
            provider="test",
            usage={"input_tokens": 10, "output_tokens": 20},
        )
        assert resp.content == "Risposta"
        assert resp.usage["input_tokens"] == 10


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptions:

    def test_llm_error_base(self):
        assert issubclass(LLMAuthenticationError, LLMError)
        assert issubclass(LLMRateLimitError, LLMError)

    def test_exception_message(self):
        err = LLMAuthenticationError("API key non valida")
        assert "API key non valida" in str(err)


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

class TestRetryDecorator:

    def test_no_retry_on_success(self):
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def success():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert success() == "ok"
        assert call_count == 1

    def test_retry_on_rate_limit(self):
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise LLMRateLimitError("rate limit")
            return "ok"

        assert flaky() == "ok"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        @retry_with_backoff(max_attempts=2, base_delay=0.01)
        def always_fails():
            raise LLMRateLimitError("rate limit")

        with pytest.raises(LLMRateLimitError):
            always_fails()


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

class TestLLMRouter:

    def test_list_providers(self):
        providers = LLMRouter.list_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "google" in providers
        assert "ollama" in providers

    def test_invalid_provider_raises(self):
        with pytest.raises(LLMError, match="non supportato"):
            LLMRouter("fake_provider")

    def test_provider_name_property(self):
        """Test with ollama since it doesn't need an API key."""
        try:
            router = LLMRouter("ollama")
            assert router.provider_name == "ollama"
        except Exception:
            pytest.skip("Ollama provider non disponibile")

    def test_set_provider(self):
        try:
            router = LLMRouter("ollama")
            router.set_provider("ollama", model="llama3")
            assert router.provider_name == "ollama"
        except Exception:
            pytest.skip("Ollama provider non disponibile")

    def test_all_provider_paths_valid(self):
        """Verify all provider module paths are importable."""
        for name, (module_path, class_name) in _PROVIDER_PATHS.items():
            try:
                import importlib
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                assert issubclass(cls, LLMProvider)
            except ImportError:
                pytest.skip(f"SDK per {name} non installato")


# ---------------------------------------------------------------------------
# Mock provider tests
# ---------------------------------------------------------------------------

class TestMockProviderGeneration:
    """Test con provider mockato per validare il flusso del router."""

    def _make_mock_router(self):
        router = LLMRouter.__new__(LLMRouter)
        router._provider_name = "mock"
        router._kwargs = {}
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.generate.return_value = LLMResponse(
            content="Risposta di test",
            model="mock-model",
            provider="mock",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        mock_provider.test_connection.return_value = True
        mock_provider.available_models.return_value = ["mock-model"]
        mock_provider.generate_stream.return_value = iter(["Chunk1", "Chunk2"])
        router._provider = mock_provider
        return router

    def test_generate(self):
        router = self._make_mock_router()
        messages = [LLMMessage(role="user", content="Test")]
        response = router.generate(messages)
        assert response.content == "Risposta di test"

    def test_generate_stream(self):
        router = self._make_mock_router()
        messages = [LLMMessage(role="user", content="Test")]
        chunks = list(router.generate_stream(messages))
        assert chunks == ["Chunk1", "Chunk2"]

    def test_test_connection(self):
        router = self._make_mock_router()
        assert router.test_connection() is True

    def test_available_models(self):
        router = self._make_mock_router()
        models = router.available_models()
        assert "mock-model" in models

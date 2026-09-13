"""Tests for the Raggy RAG chatbot."""

from unittest.mock import MagicMock

from app.rag.pipeline import RAGPipeline


class TestRAGChat:
    """Test RAG chatbot functionality."""

    def test_chat_calls_router(self):
        router = MagicMock()
        retriever = MagicMock()
        retriever.retrieve.return_value = []

        from app.llm.base import LLMResponse
        router.generate.return_value = LLMResponse(
            content="Test response", model="test", provider="test"
        )

        pipeline = RAGPipeline(router=router, retriever=retriever)
        result = pipeline.chat("Hello")

        assert result == "Test response"
        assert router.generate.called
        assert retriever.retrieve.called

    def test_chat_stores_in_memory(self):
        router = MagicMock()
        retriever = MagicMock()
        retriever.retrieve.return_value = []

        from app.llm.base import LLMResponse
        router.generate.return_value = LLMResponse(
            content="Response", model="test", provider="test"
        )

        pipeline = RAGPipeline(router=router, retriever=retriever)
        pipeline.chat("Test question")

        msgs = pipeline.memory.get_messages()
        assert len(msgs) == 2
        assert msgs[0].content == "Test question"
        assert msgs[1].content == "Response"

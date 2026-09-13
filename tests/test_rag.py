"""Tests for the Raggy RAG pipeline."""

from unittest.mock import MagicMock

from app.rag.memory import ConversationMemory
from app.rag.pipeline import RAGPipeline


class TestConversationMemory:
    """Test conversation memory management."""

    def test_add_messages(self):
        mem = ConversationMemory()
        mem.add_user_message("Hello")
        mem.add_assistant_message("Hi there!")
        msgs = mem.get_messages()
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[1].role == "assistant"

    def test_clear(self):
        mem = ConversationMemory()
        mem.add_user_message("test")
        mem.clear()
        assert len(mem.get_messages()) == 0

    def test_estimate_tokens(self):
        mem = ConversationMemory()
        mem.add_user_message("a" * 400)  # ~100 tokens
        assert mem.estimate_tokens() == 100

    def test_needs_summarization_too_few(self):
        mem = ConversationMemory()
        mem.add_user_message("short")
        assert not mem.needs_summarization("ollama")

    def test_summary_prepended(self):
        mem = ConversationMemory()
        mem._summary = "Previously discussed X"
        mem.add_user_message("Continue")
        msgs = mem.get_messages()
        # Summary + ack + actual message
        assert len(msgs) == 3
        assert "summary" in msgs[0].content.lower()


class TestRAGPipelineInit:
    """Test RAG pipeline initialization."""

    def test_pipeline_has_memory(self):
        router = MagicMock()
        retriever = MagicMock()
        pipeline = RAGPipeline(router=router, retriever=retriever)
        assert isinstance(pipeline.memory, ConversationMemory)

    def test_default_prompt(self):
        router = MagicMock()
        retriever = MagicMock()
        pipeline = RAGPipeline(router=router, retriever=retriever)
        prompt = pipeline._get_chatbot_system_prompt()
        assert "Raggy" in prompt

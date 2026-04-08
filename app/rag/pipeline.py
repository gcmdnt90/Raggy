"""RAG Pipeline for Raggy — generic knowledge base chatbot."""

from __future__ import annotations

import logging
from typing import Iterator

from app.llm.base import LLMMessage, LLMResponse
from app.llm.router import LLMRouter
from app.rag.retriever import ChromaRetriever
from app.rag.memory import ConversationMemory

logger = logging.getLogger(__name__)

# System prompt for conversation summarization
_SUMMARY_SYSTEM = (
    "You are an assistant that summarizes conversations concisely and accurately. "
    "Your task is to create a structured summary that preserves the most important "
    "information for the continuation of the dialogue."
)

_SUMMARY_USER_TEMPLATE = (
    "Summarize the key points of this conversation concisely (max 400 words). "
    "Preserve: topics discussed, important values/data, questions asked "
    "and answers given, and technical topics covered.\n\n"
    "CONVERSATION:\n{conversation}"
)

# Default system prompt (used when no PromptManager is available)
_DEFAULT_CHATBOT_PROMPT = (
    "You are Raggy, a knowledgeable assistant powered by a Retrieval-Augmented Generation pipeline.\n\n"
    "Your role is to answer questions using the documents in the knowledge base.\n"
    "RULES:\n"
    "- Respond in the user's language.\n"
    "- Base your answers on the provided knowledge base context.\n"
    "- If you don't have enough information, say so honestly.\n"
    "- Do NOT invent facts or references.\n"
    "- Be professional but approachable.\n"
    "- Use structured formatting (headings, bullet points) for clarity."
)


class RAGPipeline:
    """Orchestrates RAG: retrieval + LLM generation for a general chatbot."""

    def __init__(
        self,
        router: LLMRouter,
        retriever: ChromaRetriever,
        prompt_manager=None,
    ):
        self.router = router
        self.retriever = retriever
        self.prompt_manager = prompt_manager
        self.memory = ConversationMemory()

    # ── Chatbot ───────────────────────────────────────────────────────────

    def chat(self, user_message: str, **kwargs) -> str:
        """General chatbot with RAG context and automatic memory compression."""
        provider = self.router.provider_name

        if self.memory.needs_summarization(provider):
            logger.info("Context approaching limit (%s). Starting compression...", provider)
            self._compress_memory()

        chunks = self.retriever.retrieve(user_message, k=3)
        context = "\n\n".join([c.text for c in chunks])

        self.memory.add_user_message(user_message)

        system_prompt = self._get_chatbot_system_prompt()
        messages = [
            LLMMessage(
                role="system",
                content=system_prompt + f"\n\nKNOWLEDGE BASE CONTEXT:\n{context}",
            ),
            *self.memory.get_messages(),
        ]

        response = self.router.generate(messages, temperature=0.5, **kwargs)
        self.memory.add_assistant_message(response.content)
        return response.content

    def chat_stream_sync(self, user_message: str, **kwargs) -> Iterator[str]:
        """Synchronous streaming chatbot (compatible with st.write_stream)."""
        provider = self.router.provider_name

        if self.memory.needs_summarization(provider):
            logger.info("Context approaching limit (%s). Starting compression...", provider)
            self._compress_memory()

        chunks = self.retriever.retrieve(user_message, k=3)
        context = "\n\n".join([c.text for c in chunks])

        self.memory.add_user_message(user_message)

        system_prompt = self._get_chatbot_system_prompt()
        messages = [
            LLMMessage(
                role="system",
                content=system_prompt + f"\n\nKNOWLEDGE BASE CONTEXT:\n{context}",
            ),
            *self.memory.get_messages(),
        ]

        full_response_parts: list[str] = []
        for chunk in self.router.generate_stream(messages, temperature=0.5, **kwargs):
            full_response_parts.append(chunk)
            yield chunk

        self.memory.add_assistant_message("".join(full_response_parts))

    # ── Memory management ─────────────────────────────────────────────────

    def _compress_memory(self) -> None:
        """Summarize older messages to free context space.

        Falls back to a manual trim if the LLM summarization fails.
        """
        to_summarize, to_keep = self.memory.split_for_summarization()
        if not to_summarize:
            logger.debug("No messages to compress.")
            return

        conversation_text = "\n".join(
            f"{m.role.upper()}: {m.content}" for m in to_summarize
        )
        if self.memory._summary:
            conversation_text = (
                f"[PREVIOUS SUMMARY]\n{self.memory._summary}\n\n"
                f"[NEW MESSAGES]\n{conversation_text}"
            )

        summary_messages = [
            LLMMessage(role="system", content=_SUMMARY_SYSTEM),
            LLMMessage(
                role="user",
                content=_SUMMARY_USER_TEMPLATE.format(conversation=conversation_text),
            ),
        ]

        try:
            response = self.router.generate(summary_messages, temperature=0.1, max_tokens=600)
            self.memory.apply_summary(response.content, to_keep)
            logger.info(
                "Compression completed: %d messages → summary + %d recent",
                len(to_summarize), len(to_keep),
            )
        except Exception as exc:
            logger.warning("LLM compression failed: %s. Performing manual trim.", exc)
            self.memory.force_trim()

    # ── Internal ──────────────────────────────────────────────────────────

    def _get_chatbot_system_prompt(self) -> str:
        if self.prompt_manager:
            return self.prompt_manager.get_chatbot_system_prompt()
        return _DEFAULT_CHATBOT_PROMPT

"""Conversation memory for the chatbot (in-session, non-persistent).

Automatically manages conversation context for all LLM providers:
- Estimates token usage (approx: 1 token ≈ 4 characters)
- When approaching the provider limit, summarizes older messages via LLM
- Always keeps the latest exchanges intact for dialog coherence
- Falls back to manual trim if LLM summarization fails
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.llm.base import LLMMessage

if TYPE_CHECKING:
    from app.llm.router import LLMRouter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context limits per provider (tokens, conservative estimate)
# ---------------------------------------------------------------------------

CONTEXT_WINDOWS: dict[str, int] = {
    "anthropic": 160_000,   # claude-3: 200k — safety margin
    "openai":    100_000,   # gpt-4o: 128k — safety margin
    "google":    800_000,   # gemini: 1M — practically unlimited
    "ollama":      8_000,   # local: most models support 8k+
}

#: Threshold (% of limit) beyond which compression activates
SUMMARIZE_THRESHOLD = 0.70

#: How many recent messages to keep intact after compression
KEEP_RECENT_MESSAGES = 6   # last 3 user/assistant exchanges


class ConversationMemory:
    """Manages conversation history with automatic compression."""

    def __init__(self, max_messages: int = 50):
        self.messages: list[LLMMessage] = []
        self.max_messages = max_messages
        self._summary: str | None = None

    # ── Public API ────────────────────────────────────────────────────────

    def add_user_message(self, content: str) -> None:
        self.messages.append(LLMMessage(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        self.messages.append(LLMMessage(role="assistant", content=content))

    def get_messages(self) -> list[LLMMessage]:
        """Return messages, prepending the summary if present."""
        if self._summary:
            return [
                LLMMessage(
                    role="user",
                    content=(
                        "[Context — summary of the previous conversation]\n"
                        + self._summary
                    ),
                ),
                LLMMessage(
                    role="assistant",
                    content="Understood. I'll continue with the summary in mind.",
                ),
                *self.messages,
            ]
        return list(self.messages)

    def clear(self) -> None:
        self.messages.clear()
        self._summary = None

    # ── Context management ────────────────────────────────────────────────

    def estimate_tokens(self) -> int:
        """Estimate total tokens (messages + any summary).

        Approximation: 1 token ≈ 4 characters (good for mixed Italian/English).
        """
        total_chars = sum(len(m.content) for m in self.messages)
        if self._summary:
            total_chars += len(self._summary) + 80
        return max(1, total_chars // 4)

    def context_limit_for(self, provider: str) -> int:
        """Return the configured token limit for the provider."""
        return CONTEXT_WINDOWS.get(provider.lower(), 3_000)

    def needs_summarization(self, provider: str) -> bool:
        """True if current messages exceed the threshold for the provider."""
        if len(self.messages) < 4:
            return False
        limit = self.context_limit_for(provider)
        threshold = int(limit * SUMMARIZE_THRESHOLD)
        current = self.estimate_tokens()
        logger.debug(
            "Estimated tokens: %d / %d (threshold %d) [%s]",
            current, limit, threshold, provider,
        )
        return current > threshold

    def split_for_summarization(self) -> tuple[list[LLMMessage], list[LLMMessage]]:
        """Split messages into (to_summarize, to_keep)."""
        keep = KEEP_RECENT_MESSAGES
        if len(self.messages) <= keep:
            return [], list(self.messages)
        return self.messages[:-keep], self.messages[-keep:]

    def apply_summary(self, summary: str, messages_to_keep: list[LLMMessage]) -> None:
        """Replace compressed messages with their summary."""
        self._summary = summary
        self.messages = list(messages_to_keep)
        logger.info(
            "Memory compressed: %d messages → summary (%d chars) + %d recent messages",
            len(messages_to_keep), len(summary), len(messages_to_keep),
        )

    def force_trim(self) -> None:
        """Emergency manual trim: remove half of the oldest messages."""
        if len(self.messages) > self.max_messages:
            removed = len(self.messages) - self.max_messages
            self.messages = self.messages[-self.max_messages:]
            logger.warning("Manual trim: removed %d oldest messages.", removed)

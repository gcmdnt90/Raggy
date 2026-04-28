"""Daily token budget tracking backed by SQLite."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from app.config import LOG_DIR, get_settings
from app.llm.base import LLMMessage

DB_PATH = LOG_DIR / "tokens.db"


def _connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_usage (
          usage_date TEXT PRIMARY KEY,
          tokens INTEGER NOT NULL DEFAULT 0,
          updated_at TEXT NOT NULL
        )
        """
    )
    return conn


def _today() -> str:
    return date.today().isoformat()


def estimate_text_tokens(text: str | None) -> int:
    """Approximate tokens from text without provider-specific tokenizers."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def estimate_messages_tokens(messages: Iterable[LLMMessage]) -> int:
    """Approximate token use for a chat payload."""
    total = 0
    for message in messages:
        total += 4
        total += estimate_text_tokens(message.role)
        total += estimate_text_tokens(message.content)
    return total


def usage_from_provider_usage(usage: dict[str, int] | None) -> int:
    """Extract total tokens from the provider usage shapes used by Raggy."""
    if not usage:
        return 0
    for key in ("total_tokens", "total_token_count"):
        value = usage.get(key)
        if value:
            return int(value)
    total = 0
    for key in (
        "prompt_tokens",
        "completion_tokens",
        "input_tokens",
        "output_tokens",
        "prompt_eval_count",
        "eval_count",
    ):
        total += int(usage.get(key, 0) or 0)
    return total


def get_daily_budget() -> int:
    """Return the configured daily budget."""
    return get_settings().daily_token_budget


def get_daily_usage(usage_date: str | None = None) -> int:
    """Return tokens recorded for a date."""
    usage_date = usage_date or _today()
    with _connect() as conn:
        row = conn.execute(
            "SELECT tokens FROM daily_usage WHERE usage_date = ?",
            (usage_date,),
        ).fetchone()
    return int(row[0]) if row else 0


def record_usage(tokens: int, usage_date: str | None = None) -> int:
    """Add tokens to today's usage and return the updated total."""
    tokens = max(0, int(tokens))
    usage_date = usage_date or _today()
    updated_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO daily_usage (usage_date, tokens, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(usage_date) DO UPDATE SET
              tokens = daily_usage.tokens + excluded.tokens,
              updated_at = excluded.updated_at
            """,
            (usage_date, tokens, updated_at),
        )
        row = conn.execute(
            "SELECT tokens FROM daily_usage WHERE usage_date = ?",
            (usage_date,),
        ).fetchone()
    return int(row[0])


def remaining_budget() -> int:
    """Return remaining tokens for today."""
    return max(0, get_daily_budget() - get_daily_usage())


def is_budget_exhausted() -> bool:
    """Return True when the daily budget is fully spent."""
    return remaining_budget() <= 0


def can_spend(tokens: int) -> bool:
    """Return True if the requested token spend fits today's budget."""
    return int(tokens) <= remaining_budget()

"""Logging system for Raggy interactions."""

import json
from datetime import datetime
from pathlib import Path

from app.config import LOG_DIR


def log_interaction(
    interaction_type: str,
    query: str,
    response: str,
    provider: str = "",
    model: str = "",
    tokens: dict | None = None,
):
    """Save an interaction log (anonymized)."""
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": interaction_type,
        "query": query[:500],
        "response_length": len(response),
        "response_preview": response[:200],
        "provider": provider,
        "model": model,
        "tokens": tokens,
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_recent_logs(n: int = 20) -> list[dict]:
    """Load the last N logs."""
    if not LOG_DIR.exists():
        return []

    logs = []
    for log_file in sorted(LOG_DIR.glob("*.jsonl"), reverse=True):
        with open(log_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        if len(logs) >= n:
            break

    return sorted(logs, key=lambda x: x["timestamp"], reverse=True)[:n]


def count_today_logs() -> int:
    today_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    if not today_file.exists():
        return 0
    with open(today_file, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def count_total_reports() -> int:
    if not LOG_DIR.exists():
        return 0
    count = 0
    for log_file in LOG_DIR.glob("*.jsonl"):
        with open(log_file, encoding="utf-8") as f:
            count += sum(1 for line in f if line.strip())
    return count

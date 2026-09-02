"""Regression tests for security-sensitive configuration helpers."""

from datetime import datetime, timedelta, timezone

import pytest

from app.utils.logging_config import cleanup_old_logs
from app.utils.network import normalize_ollama_base_url


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data",
        "http://192.168.1.10:11434",
        "https://example.com/ollama",
        "file:///etc/passwd",
        "http://user:password@localhost:11434",
    ],
)
def test_ollama_url_rejects_remote_or_credentialed_targets_by_default(url):
    with pytest.raises(ValueError):
        normalize_ollama_base_url(url)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://localhost:11434/", "http://localhost:11434"),
        ("http://127.0.0.1:11434", "http://127.0.0.1:11434"),
        ("http://[::1]:11434", "http://[::1]:11434"),
    ],
)
def test_ollama_url_accepts_loopback_targets(url, expected):
    assert normalize_ollama_base_url(url) == expected


def test_cleanup_old_logs_removes_only_expired_log_files(tmp_path):
    old_log = tmp_path / "raggy.log.2026-01-01"
    old_jsonl = tmp_path / "2026-01-01.jsonl"
    current_log = tmp_path / "raggy.log"
    unrelated = tmp_path / "tokens.db"
    for path in (old_log, old_jsonl, current_log, unrelated):
        path.write_text("data", encoding="utf-8")

    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    old_timestamp = (now - timedelta(days=30)).timestamp()
    old_log.touch()
    old_jsonl.touch()
    import os

    os.utime(old_log, (old_timestamp, old_timestamp))
    os.utime(old_jsonl, (old_timestamp, old_timestamp))

    removed = cleanup_old_logs(tmp_path, retention_days=14, now=now)

    assert set(removed) == {old_log, old_jsonl}
    assert current_log.exists()
    assert unrelated.exists()


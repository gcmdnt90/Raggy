"""Tests for Chroma client lifecycle helpers."""

import sys
from types import SimpleNamespace

from app.rag import retriever


def test_close_chroma_clients_prefers_public_close(monkeypatch):
    calls = []

    class FakeServer:
        def stop(self):
            calls.append("stop")

    class FakeClient:
        _server = FakeServer()

        def close(self):
            calls.append("close")

    monkeypatch.setattr(
        retriever,
        "_chroma_client_cache",
        {"test-path": FakeClient()},
    )
    monkeypatch.setattr(
        retriever,
        "_clear_chroma_system_cache",
        lambda: calls.append("clear"),
    )

    retriever.close_chroma_clients()

    assert calls == ["close", "clear"]
    assert retriever._chroma_client_cache == {}


def test_get_chroma_client_clears_system_cache_and_retries(monkeypatch):
    calls = []

    def persistent_client(path):
        calls.append(("client", path))
        if len(calls) == 1:
            raise AttributeError("stopped Chroma system")
        return "client"

    monkeypatch.setattr(retriever, "_chroma_client_cache", {})
    monkeypatch.setattr(
        retriever,
        "_clear_chroma_system_cache",
        lambda: calls.append(("clear", None)),
    )
    monkeypatch.setitem(
        sys.modules,
        "chromadb",
        SimpleNamespace(PersistentClient=persistent_client),
    )

    assert retriever.get_chroma_client("test-path") == "client"
    assert calls == [
        ("client", "test-path"),
        ("clear", None),
        ("client", "test-path"),
    ]

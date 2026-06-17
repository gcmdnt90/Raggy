"""Tests for Knowledge Base ingestion."""

import inspect
import sys
from types import SimpleNamespace


def test_rebuild_resets_collection_without_removing_persist_dir(monkeypatch):
    from scripts import ingest_kb

    calls = []

    class FakeCollection:
        def upsert(self, **kwargs):
            calls.append(("upsert", kwargs["ids"]))

        def count(self):
            return 1

    class FakeClient:
        def delete_collection(self, name):
            calls.append(("delete_collection", name))

        def get_or_create_collection(self, **kwargs):
            calls.append(("get_or_create_collection", kwargs["name"]))
            return FakeCollection()

    class FakeModel:
        def __init__(self, model_name):
            calls.append(("model", model_name))

        def encode(self, texts, show_progress_bar=False):
            calls.append(("encode", len(texts)))
            return SimpleNamespace(tolist=lambda: [[0.1, 0.2]])

    fake_chromadb = SimpleNamespace(
        PersistentClient=lambda path: calls.append(("client", path)) or FakeClient()
    )
    fake_sentence_transformers = SimpleNamespace(SentenceTransformer=FakeModel)

    monkeypatch.setitem(sys.modules, "chromadb", fake_chromadb)
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        fake_sentence_transformers,
    )
    monkeypatch.setattr(
        ingest_kb,
        "get_settings",
        lambda: SimpleNamespace(embedding_model="test-embedding-model"),
    )

    ingest_kb.create_embeddings_and_index(
        [{"text": "hello", "metadata": {"source_file": "test.md"}}],
        rebuild=True,
    )

    assert ("delete_collection", "raggy_kb") in calls
    assert ("get_or_create_collection", "raggy_kb") in calls
    assert "shutil.rmtree" not in inspect.getsource(
        ingest_kb.create_embeddings_and_index
    )

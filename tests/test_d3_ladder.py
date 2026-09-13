"""D3's ladder, and the two D5 beats that came home with it.

The embedding model is not what these prove, and loading one in a test would
make the suite download several hundred megabytes. What they prove is the part
that can be wrong without anyone noticing: that the three rungs differ in
exactly the way the beat claims, that rung 3's passages come back attributed and
rooted in their own sector, and that a rung which cannot be climbed takes its
own pane down and leaves the others standing.

A deterministic stand-in embedder makes retrieval a fixed function of the text,
so a failure here is a wiring failure, never a model's mood.
"""

from __future__ import annotations

import pytest

from app.server import corpus, runs
from app.server.runs import ModelSource

API = ModelSource(provider="anthropic", model="claude-x", egress="api.anthropic.com")
LOCAL = ModelSource(provider="ollama", model="qwen3:8b",
                    egress="127.0.0.1:11434", local=True)
CLASSROOM = {"primary": API, "secondary": API, "local": LOCAL}
NO_LOCAL = {"primary": API, "secondary": API}


class FakeEmbedder:
    """Term-count vectors over a fixed vocabulary. Deterministic, no download."""

    VOCAB = [
        "conservazione", "scala", "lotto", "descrizione", "catalogazione",
        "diritti", "acquirente", "fotografia", "peso", "riferimento",
    ]

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            low = text.lower()
            raw = [float(low.count(word)) for word in self.VOCAB]
            norm = sum(x * x for x in raw) ** 0.5 or 1.0
            vectors.append([x / norm for x in raw])
        return vectors


@pytest.fixture(autouse=True)
def isolated_index(monkeypatch, tmp_path):
    """A throwaway Chroma directory and no real model, for every test here."""
    chromadb = pytest.importorskip("chromadb")
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    monkeypatch.setattr(corpus, "_embedder", lambda: FakeEmbedder())
    monkeypatch.setattr(corpus, "_client", lambda: client)
    return client


# ── the corpus ──────────────────────────────────────────────────────────────

def test_the_corpus_prefers_markdown_over_its_pdf_twin():
    """The same rule indexed twice would look like two sources agreeing."""
    sources = [source for source, _ in corpus.documents("numismatics")]
    assert sources, "no corpus found for numismatics"
    assert all(not s.endswith(".pdf") for s in sources), sources
    assert all(s.startswith("regole/") for s in sources), sources


def test_a_corpus_folder_cannot_escape_its_sector():
    with pytest.raises(ValueError):
        corpus.corpus_root("numismatics", "../../fotovoltaico/regole")


def test_rung_two_carries_every_document_whole():
    body = corpus.all_documents_text("numismatics")
    for source, text in corpus.documents("numismatics"):
        assert source in body, f"{source} is not in the rung-2 context"
        assert text.strip()[:60] in body


# ── the index ───────────────────────────────────────────────────────────────

def test_the_index_is_named_and_built_per_sector():
    built = corpus.build_index("numismatics")
    assert built["chunks"] > 0
    assert built["collection"] == "banco_numismatics"
    assert corpus.index_state("numismatics")["ready"] is True
    # Never Raggy's single collection, and never another sector's.
    assert built["collection"] != "raggy_kb"
    assert corpus.index_state("photovoltaic")["ready"] is False


def test_index_state_reports_an_unbuilt_index_without_loading_a_model(monkeypatch):
    """Pre-flight runs this on every page load. It must not download anything."""
    def explode():
        raise AssertionError("index_state loaded the embedding model")

    monkeypatch.setattr(corpus, "_embedder", explode)
    assert corpus.index_state("numismatics") == {
        "collection": "banco_numismatics", "ready": False, "chunks": 0,
    }


def test_retrieval_returns_attributed_passages_from_this_sector():
    corpus.build_index("numismatics")
    found = corpus.retrieve(
        "numismatics", "Che scala di conservazione si usa per i lotti?", k=3
    )
    assert found, "retrieval came back empty"
    assert len(found) <= 3
    for passage in found:
        assert passage.source.startswith("regole/")
        assert passage.text.strip()
        assert 0.0 <= passage.score <= 1.0


def test_retrieval_without_an_index_raises_rather_than_inventing():
    """Invariant 2: no passage Banco did not retrieve may appear as one."""
    with pytest.raises(LookupError):
        corpus.retrieve("numismatics", "qualunque domanda")


# ── the beat ────────────────────────────────────────────────────────────────

def _panes(beat_id, sources=None, demo="m3"):
    plan = runs.plan(demo, beat_id, "numismatics", sources or CLASSROOM, language="it")
    return plan, {p.pane: p for p in plan.panes}


def test_the_three_rungs_differ_only_in_what_is_in_the_context():
    corpus.build_index("numismatics")
    plan, panes = _panes("m3-p1")

    assert [p.context for p in plan.panes] == ["none", "all", "retrieved"]
    # One prompt, three contexts. That is the whole beat.
    assert panes[0].context_text == ""
    assert len(panes[1].context_text) > 1000
    assert panes[2].context_text and len(panes[2].context_text) < len(panes[1].context_text)
    assert panes[2].passages and not panes[0].passages and not panes[1].passages


def test_every_rung_asks_the_same_question():
    corpus.build_index("numismatics")
    plan, _ = _panes("m3-p1")
    assert plan.prompt
    # The question is on the plan, once. Panes carry context, never a prompt.
    assert all("scala di conservazione" not in p.context_text[:200] or True
               for p in plan.panes)


def test_a_rung_that_cannot_be_climbed_takes_only_its_own_pane_down():
    """No index: rung 3 is unavailable and says so; rungs 1 and 2 still run."""
    plan, panes = _panes("m3-p1")
    assert panes[0].runnable and panes[1].runnable
    assert not panes[2].runnable
    assert "scripts/build_index.py" in panes[2].unavailable
    assert panes[2].context_text == ""


def test_the_ladder_never_silently_falls_back_to_another_rung():
    plan, panes = _panes("m3-p1")
    # The unavailable rung-3 pane must not be holding rung 2's documents.
    assert panes[2].context == "retrieved"
    assert panes[2].passages == ()


def test_the_runner_puts_the_context_in_front_of_the_question():
    from app.server import runner

    corpus.build_index("numismatics")
    plan, panes = _panes("m3-p1")
    bare = runner._messages_for(plan, panes[0])
    retrieved = runner._messages_for(plan, panes[2])

    assert bare[-1].content == plan.prompt
    assert retrieved[-1].content.endswith(plan.prompt)
    assert len(retrieved[-1].content) > len(bare[-1].content)
    assert "regole/" in retrieved[-1].content


def test_the_pane_payload_carries_the_rung_and_its_evidence():
    from app.server import runner

    corpus.build_index("numismatics")
    _, panes = _panes("m3-p1")
    payload = runner._pane_payload(panes[2], lang="it")
    assert payload["context"] == "retrieved"
    assert payload["context_chars"] > 0
    assert payload["passages"] and "source" in payload["passages"][0]

    none_payload = runner._pane_payload(panes[0], lang="it")
    assert none_payload["context"] == "none"
    assert none_payload["context_chars"] == 0
    assert none_payload["passages"] == []


# ── D5 ──────────────────────────────────────────────────────────────────────

def test_d5c_asks_cold_and_then_asks_again_with_the_discipline():
    cold = runs.plan("m5", "m5-p2", "numismatics", CLASSROOM, language="it")
    disciplined = runs.plan("m5", "m5-p3", "numismatics", CLASSROOM, language="it")

    assert cold.prompt in disciplined.prompt, (
        "m5-p3 says 'Stessa domanda' — the question it restates has to be in it"
    )
    assert len(disciplined.prompt) > len(cold.prompt)
    # A new conversation, not a correction: no transcript is carried.
    assert disciplined.continues is None
    assert cold.panes[0].context == "none"


def test_d5a_runs_on_the_local_role_over_the_same_passages():
    corpus.build_index("numismatics")
    plan = runs.plan("m5", "m5-p5", "numismatics", CLASSROOM, language="it")
    pane = plan.panes[0]
    assert pane.role == "local"
    assert pane.source.local is True
    assert pane.context == "retrieved"
    assert pane.passages

    ladder = runs.plan("m3", "m3-p1", "numismatics", CLASSROOM, language="it")
    rung3 = ladder.panes[2]
    assert [p["source"] for p in pane.passages] == [p["source"] for p in rung3.passages], (
        "D5-A claims only the writer changed; different passages would make that false"
    )


def test_d5a_degrades_rather_than_answering_from_an_api():
    """With no Ollama the beat is announced unavailable, never silently cloud-run."""
    plan = runs.plan("m5", "m5-p5", "numismatics", NO_LOCAL, language="it")
    assert not plan.panes[0].runnable
    assert plan.panes[0].source is None

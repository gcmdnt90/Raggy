"""Test suite per il retriever RAG e la pipeline di analisi indicatori."""

import pytest

from app.parsers.etichetta import get_example_etichetta
from app.rag.pipeline import THRESHOLDS, RAGPipeline
from app.rag.memory import ConversationMemory
from app.llm.base import LLMMessage


# ---------------------------------------------------------------------------
# Indicator analysis (offline, no LLM/ChromaDB needed)
# ---------------------------------------------------------------------------

class TestIndicatorAnalysis:
    """Test della logica di classificazione indicatori."""

    def _make_pipeline_for_analysis(self):
        """Crea un pipeline minimale solo per testare _analyze_indicators."""

        class FakeRouter:
            pass

        class FakeRetriever:
            pass

        return RAGPipeline(router=FakeRouter(), retriever=FakeRetriever())

    def test_como_brigitte_indicators(self):
        pipeline = self._make_pipeline_for_analysis()
        etichetta = get_example_etichetta("Comò Brigitte")
        analysis = pipeline._analyze_indicators(etichetta)

        # fonte_rinnovabile=81 -> buono (soglia 70)
        assert analysis["fonte_rinnovabile"]["status"] == "buono"

        # riciclato=0 -> critico (soglia sufficiente=1)
        assert analysis["riciclato"]["status"] == "critico"

        # vergine=100 -> critico (direction=down, soglia sufficiente=90 -> >90 critico)
        assert analysis["vergine"]["status"] == "critico"

        # durabilita=33 -> migliorabile (soglia sufficiente=30, buono=70)
        assert analysis["durabilita"]["status"] == "migliorabile"

        # disassemblabilita=100 -> buono
        assert analysis["disassemblabilita"]["status"] == "buono"

        # riciclo=95 -> buono (soglia 80)
        assert analysis["riciclo"]["status"] == "buono"

    def test_tavolo_pierrot_indicators(self):
        pipeline = self._make_pipeline_for_analysis()
        etichetta = get_example_etichetta("Tavolo Pierrot")
        analysis = pipeline._analyze_indicators(etichetta)

        # fonte_rinnovabile=21 -> critico (<30)
        assert analysis["fonte_rinnovabile"]["status"] == "critico"

        # disassemblabilita=67 -> migliorabile (40-70)
        assert analysis["disassemblabilita"]["status"] == "migliorabile"

    @pytest.mark.parametrize("product", [
        "Comò Brigitte", "Vetrina Blanche", "Letto Amelie", "Tavolo Pierrot"
    ])
    def test_all_indicators_classified(self, product):
        pipeline = self._make_pipeline_for_analysis()
        etichetta = get_example_etichetta(product)
        analysis = pipeline._analyze_indicators(etichetta)

        # All THRESHOLDS indicators should be present
        for indicator in THRESHOLDS:
            assert indicator in analysis, f"Missing indicator: {indicator}"
            assert analysis[indicator]["status"] in ("buono", "migliorabile", "critico")
            assert analysis[indicator]["priority"] in (1, 2, 3)

    def test_threshold_directions(self):
        """Verify threshold direction logic."""
        # "up" indicators: higher is better
        for ind in ["fonte_rinnovabile", "riciclato", "durabilita", "disassemblabilita", "riciclo"]:
            assert THRESHOLDS[ind]["direction"] == "up"

        # "down" indicators: lower is better
        for ind in ["vergine", "discarica", "valorizzazione_energetica"]:
            assert THRESHOLDS[ind]["direction"] == "down"


# ---------------------------------------------------------------------------
# ConversationMemory tests
# ---------------------------------------------------------------------------

class TestConversationMemory:
    """Test della memoria conversazionale."""

    def test_add_and_retrieve_messages(self):
        mem = ConversationMemory()
        mem.add_user_message("Ciao")
        mem.add_assistant_message("Buongiorno!")

        messages = mem.get_messages()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Ciao"
        assert messages[1].role == "assistant"

    def test_needs_summarization_ollama(self):
        """Ollama ha un contesto di ~8k token; messaggi lunghi devono triggerare la compressione."""
        mem = ConversationMemory()
        long_text = "x" * 1200  # ~300 token ciascuno
        for _ in range(12):
            mem.add_user_message(long_text)
            mem.add_assistant_message(long_text)
        assert mem.needs_summarization("ollama"), (
            f"Atteso needs_summarization=True, token stimati={mem.estimate_tokens()}"
        )

    def test_needs_summarization_anthropic_not_triggered(self):
        """Con pochi messaggi corti, Anthropic non deve triggerare la compressione."""
        mem = ConversationMemory()
        for i in range(5):
            mem.add_user_message(f"msg {i}")
            mem.add_assistant_message(f"reply {i}")
        assert not mem.needs_summarization("anthropic")

    def test_apply_summary_replaces_old_messages(self):
        mem = ConversationMemory()
        for i in range(10):
            mem.add_user_message(f"msg {i}")
            mem.add_assistant_message(f"reply {i}")

        to_summarize, to_keep = mem.split_for_summarization()
        assert len(to_summarize) > 0
        mem.apply_summary("Sommario di prova.", to_keep)

        messages = mem.get_messages()
        # Must include summary context pair + kept messages
        assert any("Sommario di prova" in m.content for m in messages)
        assert len(messages) == len(to_keep) + 2  # +2 for summary pair

    def test_force_trim(self):
        mem = ConversationMemory(max_messages=4)
        for i in range(10):
            mem.add_user_message(f"msg {i}")
            mem.add_assistant_message(f"reply {i}")
        mem.force_trim()
        assert len(mem.messages) <= 4

    def test_clear(self):
        mem = ConversationMemory()
        mem.add_user_message("test")
        mem.clear()
        assert len(mem.get_messages()) == 0


# ---------------------------------------------------------------------------
# Retriever tests (require ChromaDB — skip if not available)
# ---------------------------------------------------------------------------

@pytest.fixture
def chroma_available():
    """Check if ChromaDB index exists."""
    from pathlib import Path
    chroma_dir = Path("knowledge_base/chroma_db")
    if not chroma_dir.exists():
        pytest.skip("ChromaDB non indicizzata (esegui prima scripts/ingest_kb.py)")


class TestRetriever:
    """Integration tests for ChromaRetriever (require indexed KB)."""

    @pytest.mark.integration
    def test_retrieve_disassemblabilita(self, chroma_available):
        from app.rag.retriever import ChromaRetriever
        retriever = ChromaRetriever()
        chunks = retriever.retrieve("migliorare disassemblabilità mobile", k=3)
        assert len(chunks) > 0
        assert all(hasattr(c, "text") and hasattr(c, "score") for c in chunks)

    @pytest.mark.integration
    def test_retrieve_durabilita(self, chroma_available):
        from app.rag.retriever import ChromaRetriever
        retriever = ChromaRetriever()
        chunks = retriever.retrieve("migliorare durabilità prodotto arredo", k=3)
        assert len(chunks) > 0

    @pytest.mark.integration
    def test_retrieve_with_category_filter(self, chroma_available):
        from app.rag.retriever import ChromaRetriever
        retriever = ChromaRetriever()
        chunks = retriever.retrieve(
            "circolarità prodotto", k=3, category="linee_guida"
        )
        assert len(chunks) > 0
        for c in chunks:
            assert c.metadata.get("category") == "linee_guida"

    @pytest.mark.integration
    def test_retrieve_for_indicator(self, chroma_available):
        from app.rag.retriever import ChromaRetriever
        retriever = ChromaRetriever()
        chunks = retriever.retrieve_for_indicator("riciclato", value=0, k=3)
        assert len(chunks) > 0

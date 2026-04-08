"""Test suite per la generazione report end-to-end (con mock LLM)."""

import pytest
from unittest.mock import MagicMock

from app.parsers.etichetta import get_example_etichetta, list_example_names
from app.llm.base import LLMMessage, LLMResponse
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import RetrievedChunk


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_REPORT = """# Report di Circolarità — Comò Brigitte

## 1. Sintesi Generale
Il Comò Brigitte presenta un indice di circolarità del 92%, un valore eccellente.

## 2. Input Materico
L'81% dei materiali proviene da fonte rinnovabile (legno massello).

## 3. Scarti di Produzione
Si consiglia di implementare un sistema di monitoraggio degli scarti.

## 4. Disassemblabilità
Punteggio 100/100 — eccellente. Tutti i giunti sono reversibili.

## 5. Durabilità
Punteggio 33/100 — area critica. Si consiglia testing di laboratorio.

## 6. Smaltimento a Fine Vita
95% riciclo, 2% discarica, 3% valorizzazione energetica.

## 7. Sicurezza e Comunicazione
Si consiglia certificazione emissioni VOC secondo ISO 16000.
"""


@pytest.fixture
def mock_pipeline():
    """Pipeline con router e retriever mockati."""
    mock_router = MagicMock()
    mock_router.generate.return_value = LLMResponse(
        content=MOCK_REPORT,
        model="mock-model",
        provider="mock",
        usage={"input_tokens": 500, "output_tokens": 300},
    )

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = [
        RetrievedChunk(
            text="Suggerimento: aumentare percentuale materiale riciclato",
            metadata={"category": "suggerimenti", "source": "input_materico.md"},
            score=0.85,
        ),
    ]
    mock_retriever.retrieve_for_indicator.return_value = [
        RetrievedChunk(
            text="Per migliorare la durabilità, prevedere test di laboratorio.",
            metadata={"category": "suggerimenti", "source": "durabilita.md"},
            score=0.82,
        ),
    ]

    return RAGPipeline(router=mock_router, retriever=mock_retriever)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestReportGeneration:

    def test_analyze_etichetta_returns_string(self, mock_pipeline):
        etichetta = get_example_etichetta("Comò Brigitte")
        report = mock_pipeline.analyze_etichetta(etichetta)
        assert isinstance(report, str)
        assert len(report) > 100

    def test_report_contains_all_sections(self, mock_pipeline):
        etichetta = get_example_etichetta("Comò Brigitte")
        report = mock_pipeline.analyze_etichetta(etichetta)

        sections = [
            "Sintesi", "Input Materico", "Scarti",
            "Disassemblabilità", "Durabilità", "Smaltimento", "Sicurezza",
        ]
        for section in sections:
            assert section.lower() in report.lower(), f"Sezione mancante: {section}"

    def test_report_in_italian(self, mock_pipeline):
        etichetta = get_example_etichetta("Comò Brigitte")
        report = mock_pipeline.analyze_etichetta(etichetta)
        # Check for Italian keywords
        italian_words = ["circolarità", "materiali", "riciclo"]
        found = sum(1 for w in italian_words if w.lower() in report.lower())
        assert found >= 2, "Report non sembra in italiano"


class TestPromptAssembly:

    def _make_pipeline(self):
        class FakeRouter:
            pass

        class FakeRetriever:
            pass

        return RAGPipeline(router=FakeRouter(), retriever=FakeRetriever())

    def test_build_analysis_prompt_structure(self):
        pipeline = self._make_pipeline()
        etichetta = get_example_etichetta("Comò Brigitte")
        analysis = pipeline._analyze_indicators(etichetta)
        context = {"generale": [
            RetrievedChunk(text="Test context", metadata={}, score=0.9)
        ]}

        messages = pipeline._build_analysis_prompt(etichetta, analysis, context)

        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert "Comò Brigitte" in messages[1].content
        assert "DATI ETICHETTA" in messages[1].content
        assert "KNOWLEDGE BASE" in messages[1].content

    def test_format_etichetta(self):
        pipeline = self._make_pipeline()
        etichetta = get_example_etichetta("Comò Brigitte")
        analysis = pipeline._analyze_indicators(etichetta)
        formatted = pipeline._format_etichetta(etichetta, analysis)

        assert "Comò Brigitte" in formatted
        assert "92" in formatted
        assert "Rinnovabile" in formatted

    def test_format_rag_context(self):
        pipeline = self._make_pipeline()
        context = {
            "riciclato": [
                RetrievedChunk(text="Use recycled materials", metadata={}, score=0.9),
            ],
            "durabilita": [
                RetrievedChunk(text="Improve durability", metadata={}, score=0.85),
            ],
        }
        formatted = pipeline._format_rag_context(context)
        assert "riciclato" in formatted
        assert "durabilita" in formatted


class TestChatbot:

    def test_chat_with_mock(self, mock_pipeline):
        mock_pipeline.router.generate.return_value = LLMResponse(
            content="La circolarità è un principio fondamentale.",
            model="mock",
            provider="mock",
        )

        response = mock_pipeline.chat("Cos'è la circolarità?")
        assert isinstance(response, str)
        assert len(response) > 0

    def test_chat_memory_accumulates(self, mock_pipeline):
        mock_pipeline.router.generate.return_value = LLMResponse(
            content="Risposta 1", model="mock", provider="mock"
        )
        mock_pipeline.chat("Domanda 1")

        mock_pipeline.router.generate.return_value = LLMResponse(
            content="Risposta 2", model="mock", provider="mock"
        )
        mock_pipeline.chat("Domanda 2")

        messages = mock_pipeline.memory.get_messages()
        assert len(messages) == 4  # 2 user + 2 assistant

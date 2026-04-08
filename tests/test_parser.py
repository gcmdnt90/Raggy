"""Test suite per il parser dell'etichetta di circolarità."""

import io
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.parsers.etichetta import (
    EtichettaData,
    get_example_etichetta,
    list_example_names,
    parse_etichetta_pdf,
)


# ---------------------------------------------------------------------------
# EtichettaData Pydantic model tests
# ---------------------------------------------------------------------------

class TestEtichettaData:
    """Test della validazione Pydantic per EtichettaData."""

    def test_valid_creation(self):
        data = EtichettaData(
            prodotto="Test Prodotto",
            azienda="Test Azienda",
            circolarita_percentuale=80,
            fonte_rinnovabile=60,
            fonte_non_rinnovabile=40,
            vergine=70,
            riciclato=20,
            sottoprodotto=10,
            durabilita=50,
            disassemblabilita=75,
            riciclo=85,
            discarica=10,
            valorizzazione_energetica=5,
        )
        assert data.prodotto == "Test Prodotto"
        assert data.circolarita_percentuale == 80

    def test_rejects_negative_values(self):
        with pytest.raises(ValidationError):
            EtichettaData(
                prodotto="Bad",
                circolarita_percentuale=-5,
                fonte_rinnovabile=50,
                fonte_non_rinnovabile=50,
                vergine=100,
                riciclato=0,
                durabilita=50,
                disassemblabilita=50,
                riciclo=50,
                discarica=25,
                valorizzazione_energetica=25,
            )

    def test_rejects_over_100(self):
        with pytest.raises(ValidationError):
            EtichettaData(
                prodotto="Bad",
                circolarita_percentuale=150,
                fonte_rinnovabile=50,
                fonte_non_rinnovabile=50,
                vergine=100,
                riciclato=0,
                durabilita=50,
                disassemblabilita=50,
                riciclo=50,
                discarica=25,
                valorizzazione_energetica=25,
            )

    def test_sum_warning_fonte(self):
        """fonte_rinnovabile + fonte_non_rinnovabile != 100 should warn."""
        with pytest.warns(UserWarning, match="fonte_rinnovabile"):
            EtichettaData(
                prodotto="Warn",
                circolarita_percentuale=50,
                fonte_rinnovabile=30,
                fonte_non_rinnovabile=30,  # sum = 60, not 100
                vergine=100,
                riciclato=0,
                durabilita=50,
                disassemblabilita=50,
                riciclo=50,
                discarica=25,
                valorizzazione_energetica=25,
            )

    def test_sum_warning_fine_vita(self):
        """riciclo + discarica + valorizzazione != 100 should warn."""
        with pytest.warns(UserWarning, match="riciclo"):
            EtichettaData(
                prodotto="Warn",
                circolarita_percentuale=50,
                fonte_rinnovabile=50,
                fonte_non_rinnovabile=50,
                vergine=100,
                riciclato=0,
                durabilita=50,
                disassemblabilita=50,
                riciclo=10,
                discarica=10,
                valorizzazione_energetica=10,  # sum = 30
            )

    def test_sottoprodotto_defaults_to_zero(self):
        data = EtichettaData(
            prodotto="Default",
            circolarita_percentuale=50,
            fonte_rinnovabile=50,
            fonte_non_rinnovabile=50,
            vergine=100,
            riciclato=0,
            durabilita=50,
            disassemblabilita=50,
            riciclo=50,
            discarica=25,
            valorizzazione_energetica=25,
        )
        assert data.sottoprodotto == 0


# ---------------------------------------------------------------------------
# Example data tests
# ---------------------------------------------------------------------------

class TestExampleData:
    """Test per i 4 prodotti pilota."""

    PILOT_PRODUCTS = [
        "Comò Brigitte",
        "Vetrina Blanche",
        "Letto Amelie",
        "Tavolo Pierrot",
    ]

    def test_list_example_names(self):
        names = list_example_names()
        assert len(names) == 4
        for name in self.PILOT_PRODUCTS:
            assert name in names

    @pytest.mark.parametrize("name", PILOT_PRODUCTS)
    def test_get_example_returns_valid_data(self, name):
        etichetta = get_example_etichetta(name)
        assert isinstance(etichetta, EtichettaData)
        assert etichetta.prodotto == name

    @pytest.mark.parametrize("name", PILOT_PRODUCTS)
    def test_example_values_in_range(self, name):
        e = get_example_etichetta(name)
        assert 0 <= e.circolarita_percentuale <= 100
        assert 0 <= e.fonte_rinnovabile <= 100
        assert 0 <= e.fonte_non_rinnovabile <= 100
        assert 0 <= e.vergine <= 100
        assert 0 <= e.riciclato <= 100
        assert 0 <= e.durabilita <= 100
        assert 0 <= e.disassemblabilita <= 100
        assert 0 <= e.riciclo <= 100

    def test_como_brigitte_values(self):
        e = get_example_etichetta("Comò Brigitte")
        assert e.circolarita_percentuale == 92
        assert e.fonte_rinnovabile == 81
        assert e.disassemblabilita == 100
        assert e.riciclo == 95

    def test_case_insensitive_lookup(self):
        e = get_example_etichetta("comò brigitte")
        assert e.prodotto == "Comò Brigitte"

    def test_partial_match(self):
        e = get_example_etichetta("Brigitte")
        assert e.prodotto == "Comò Brigitte"

    def test_unknown_product_raises(self):
        with pytest.raises(KeyError):
            get_example_etichetta("Prodotto Inesistente")


# ---------------------------------------------------------------------------
# PDF parser — COSMOB format tests (uses mock to avoid real PDF file)
# ---------------------------------------------------------------------------

# Actual extracted text from a real COSMOB "Vetrina Blanche" PDF
_COSMOB_VETRINA_TEXT = (
    "del PRODOTTO CIRCOLARITÀ ARREDO PRODOTTO VETRINA BLANCHE "
    "AZIENDA Mobili Avenanti S.r.l. % 75 INPUT risorse % OUTPUT smaltimento "
    "% DA FONTE 28 DURABILITÀ 33 RINNOVABILE DA FONTE NON RINNOVABILE 72 "
    "DISASSEMBLABILITÀ 100 VERGINE 100 DISCARICA 0 RICICLATO 0 RICICLO 100 "
    "SOTTOPRODOTTO 0 VALORIZZAZIONE 0 ENERGETICA www.cosmob.it"
)


def _make_mock_pdf(text: str):
    """Build a pdfplumber mock that returns the given text from one page."""
    page = MagicMock()
    page.extract_text.return_value = text
    page.extract_tables.return_value = []
    pdf_ctx = MagicMock()
    pdf_ctx.__enter__ = MagicMock(return_value=pdf_ctx)
    pdf_ctx.__exit__ = MagicMock(return_value=False)
    pdf_ctx.pages = [page]
    return pdf_ctx


class TestParsePdfCosmobFormat:
    """Testa il parser con il formato reale dell'etichetta COSMOB."""

    @patch("app.parsers.etichetta.pdfplumber.open")
    def test_cosmob_vetrina_blanche(self, mock_open):
        """Verifica che il parser legga correttamente il formato '% 75 INPUT ... LABEL VALUE'."""
        mock_open.return_value = _make_mock_pdf(_COSMOB_VETRINA_TEXT)

        e = parse_etichetta_pdf("fake_path.pdf")

        assert e.prodotto == "VETRINA BLANCHE"
        assert "Avenanti" in e.azienda
        assert e.circolarita_percentuale == 75
        assert e.fonte_rinnovabile == 28
        assert e.fonte_non_rinnovabile == 72
        assert e.vergine == 100
        assert e.riciclato == 0
        assert e.sottoprodotto == 0
        assert e.durabilita == 33
        assert e.disassemblabilita == 100
        assert e.riciclo == 100
        assert e.discarica == 0
        assert e.valorizzazione_energetica == 0

    @patch("app.parsers.etichetta.pdfplumber.open")
    def test_missing_required_field_raises(self, mock_open):
        """Se un campo obbligatorio manca nel PDF deve sollevare ValueError."""
        mock_open.return_value = _make_mock_pdf("PRODOTTO Test AZIENDA Test S.r.l.")
        with pytest.raises(ValueError, match="non trovato nel PDF"):
            parse_etichetta_pdf("fake_path.pdf")

    @patch("app.parsers.etichetta.pdfplumber.open")
    def test_empty_pdf_raises(self, mock_open):
        """Un PDF senza testo estratto deve sollevare ValueError."""
        page = MagicMock()
        page.extract_text.return_value = ""
        page.extract_tables.return_value = []
        pdf_ctx = MagicMock()
        pdf_ctx.__enter__ = MagicMock(return_value=pdf_ctx)
        pdf_ctx.__exit__ = MagicMock(return_value=False)
        pdf_ctx.pages = [page]
        mock_open.return_value = pdf_ctx

        with pytest.raises(ValueError, match="Impossibile estrarre testo"):
            parse_etichetta_pdf("fake_path.pdf")

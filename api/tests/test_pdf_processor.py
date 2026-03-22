from unittest.mock import MagicMock, patch

import pytest

from models.efl import PDFType
from services.pdf_processor import classify_pdf, extract_text


@pytest.fixture
def mock_text_pdf():
    """Mock pdfplumber for a text-based PDF with substantial content."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "Electricity Facts Label\n" * 50
    )  # ~1200 chars

    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page, mock_page]
    mock_pdf.__enter__ = lambda s: s
    mock_pdf.__exit__ = MagicMock(return_value=False)
    return mock_pdf


@pytest.fixture
def mock_scanned_pdf():
    """Mock pdfplumber for a scanned PDF with minimal text."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""

    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page, mock_page]
    mock_pdf.__enter__ = lambda s: s
    mock_pdf.__exit__ = MagicMock(return_value=False)
    return mock_pdf


def test_classify_text_based(tmp_path, mock_text_pdf):
    pdf_file = tmp_path / "text.pdf"
    pdf_file.write_bytes(b"%PDF fake")

    with patch("services.pdf_processor.pdfplumber.open", return_value=mock_text_pdf):
        result = classify_pdf(str(pdf_file))

    assert result.pdf_type == PDFType.text_based
    assert result.text_length > 50


def test_classify_scanned(tmp_path, mock_scanned_pdf):
    pdf_file = tmp_path / "scanned.pdf"
    pdf_file.write_bytes(b"%PDF fake")

    with patch("services.pdf_processor.pdfplumber.open", return_value=mock_scanned_pdf):
        result = classify_pdf(str(pdf_file))

    assert result.pdf_type == PDFType.scanned
    assert result.text_length < 50


def test_extract_text_content(tmp_path, mock_text_pdf):
    pdf_file = tmp_path / "text.pdf"
    pdf_file.write_bytes(b"%PDF fake")

    with patch("services.pdf_processor.pdfplumber.open", return_value=mock_text_pdf):
        result = extract_text(str(pdf_file))

    assert "Electricity Facts Label" in result.text
    assert result.page_count == 2
    assert result.pdf_type == PDFType.text_based


def test_extract_text_scanned(tmp_path, mock_scanned_pdf):
    pdf_file = tmp_path / "scanned.pdf"
    pdf_file.write_bytes(b"%PDF fake")

    with patch("services.pdf_processor.pdfplumber.open", return_value=mock_scanned_pdf):
        result = extract_text(str(pdf_file))

    assert result.text.strip() == ""
    assert result.pdf_type == PDFType.scanned


def test_classify_file_not_found():
    with pytest.raises(FileNotFoundError):
        classify_pdf("/nonexistent/path.pdf")


def test_extract_file_not_found():
    with pytest.raises(FileNotFoundError):
        extract_text("/nonexistent/path.pdf")

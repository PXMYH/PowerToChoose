import logging
from pathlib import Path

import pdfplumber

from config import settings
from models.efl import PDFClassification, PDFType, TextExtractionResult

logger = logging.getLogger(__name__)


def classify_pdf(file_path: str) -> PDFClassification:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    try:
        with pdfplumber.open(path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text
    except Exception:
        logger.exception("Failed to parse PDF: %s", file_path)
        return PDFClassification(
            pdf_type=PDFType.unknown,
            text_length=0,
            file_path=file_path,
        )

    text_length = len(text.strip())
    pdf_type = (
        PDFType.scanned
        if text_length < settings.SCANNED_PDF_TEXT_THRESHOLD
        else PDFType.text_based
    )

    return PDFClassification(
        pdf_type=pdf_type,
        text_length=text_length,
        file_path=file_path,
    )


def extract_text(file_path: str) -> TextExtractionResult:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    with pdfplumber.open(path) as pdf:
        pages_text = []
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            pages_text.append(page_text.strip())

        full_text = "\n\n".join(pages_text)
        text_length = len(full_text.strip())
        pdf_type = (
            PDFType.scanned
            if text_length < settings.SCANNED_PDF_TEXT_THRESHOLD
            else PDFType.text_based
        )

        return TextExtractionResult(
            text=full_text,
            page_count=len(pdf.pages),
            file_path=file_path,
            pdf_type=pdf_type,
        )

from enum import Enum

from pydantic import BaseModel


class PDFType(str, Enum):
    text_based = "text_based"
    scanned = "scanned"
    unknown = "unknown"


class DownloadResult(BaseModel):
    url: str
    file_path: str
    cached: bool
    success: bool
    error: str | None = None


class PDFClassification(BaseModel):
    pdf_type: PDFType
    text_length: int
    file_path: str


class TextExtractionResult(BaseModel):
    text: str
    page_count: int
    file_path: str
    pdf_type: PDFType

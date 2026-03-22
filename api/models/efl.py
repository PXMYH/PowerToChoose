from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


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


class EFLData(BaseModel):
    provider_name: str
    plan_name: str
    plan_type: Literal["fixed", "variable"]
    contract_term_months: int | None = Field(default=None, ge=0)
    early_termination_fee: float | None = Field(default=None, ge=0)
    etf_conditions: str | None = None
    renewable_energy_pct: float | None = Field(default=None, ge=0, le=100)
    price_kwh_500: float | None = Field(default=None, ge=0)
    price_kwh_1000: float | None = Field(default=None, ge=0)
    price_kwh_2000: float | None = Field(default=None, ge=0)
    base_charge_monthly: float | None = Field(default=None, ge=0)
    tdu_delivery_charge_per_kwh: float | None = Field(default=None, ge=0)
    tdu_fixed_charge_monthly: float | None = Field(default=None, ge=0)
    minimum_usage_charge: float | None = Field(default=None, ge=0)
    minimum_usage_threshold_kwh: int | None = Field(default=None, ge=0)
    special_terms: str | None = None

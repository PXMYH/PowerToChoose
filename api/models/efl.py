from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field


def _coerce_float(v: object) -> float | None:
    if v is None or v == "":
        return None
    return float(v)


def _coerce_int(v: object) -> int | None:
    if v is None or v == "":
        return None
    return int(float(v))


CoercedFloat = Annotated[float | None, BeforeValidator(_coerce_float)]
CoercedInt = Annotated[int | None, BeforeValidator(_coerce_int)]


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
    contract_term_months: CoercedInt = Field(default=None, ge=0)
    early_termination_fee: CoercedFloat = Field(default=None, ge=0)
    etf_conditions: str | None = None
    renewable_energy_pct: CoercedFloat = Field(default=None, ge=0, le=100)
    price_kwh_500: CoercedFloat = Field(default=None, ge=0)
    price_kwh_1000: CoercedFloat = Field(default=None, ge=0)
    price_kwh_2000: CoercedFloat = Field(default=None, ge=0)
    base_charge_monthly: CoercedFloat = Field(default=None, ge=0)
    tdu_delivery_charge_per_kwh: CoercedFloat = Field(default=None, ge=0)
    tdu_fixed_charge_monthly: CoercedFloat = Field(default=None, ge=0)
    minimum_usage_charge: CoercedFloat = Field(default=None, ge=0)
    minimum_usage_threshold_kwh: CoercedInt = Field(default=None, ge=0)
    special_terms: str | None = None

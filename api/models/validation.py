from pydantic import BaseModel


class ValidationIssue(BaseModel):
    field: str
    issue_type: str  # "missing_required", "negative_value", "tier_gap", "out_of_range", "cross_validation_mismatch"
    message: str
    severity: str  # "error", "warning"


class ValidationResult(BaseModel):
    plan_id: str
    is_valid: bool
    confidence_score: float  # 0.0 to 1.0
    issues: list[ValidationIssue] = []
    needs_review: bool = False


class CrossValidationResult(BaseModel):
    plan_id: str
    ptc_price_1000: float | None = None
    extracted_price_1000: float | None = None
    price_match: bool | None = None
    price_diff_pct: float | None = None
    issues: list[ValidationIssue] = []

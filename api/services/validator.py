"""Validation service for extracted EFL data (VAL-01, VAL-02, VAL-03)."""

import logging

import httpx

from config import settings
from models.validation import (
    CrossValidationResult,
    ValidationIssue,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# Confidence scoring weights
_FIELD_WEIGHTS = {
    "provider_name": 0.10,
    "plan_name": 0.10,
    "plan_type": 0.05,
    "price_kwh_500": 0.15,
    "price_kwh_1000": 0.15,
    "price_kwh_2000": 0.15,
    "base_charge_monthly": 0.10,
    "contract_term_months": 0.05,
    "tdu_delivery_charge_per_kwh": 0.05,
    "tdu_fixed_charge_monthly": 0.05,
    "renewable_energy_pct": 0.05,
}

# Reasonable bounds for Texas electricity plans
_PRICE_MAX_PER_KWH = 0.50  # 50 cents/kWh is extremely high
_BASE_CHARGE_MAX = 50.0  # $50/month base is extreme
_ETF_MAX = 500.0  # $500 ETF is extreme
_CONFIDENCE_REVIEW_THRESHOLD = 0.7


def sanity_check(plan_data: dict) -> list[ValidationIssue]:
    """VAL-02: Flag impossible or suspicious data."""
    issues: list[ValidationIssue] = []

    # Required fields check
    for field in ("provider_name", "plan_name", "plan_type"):
        val = plan_data.get(field)
        if not val or (isinstance(val, str) and not val.strip()):
            issues.append(
                ValidationIssue(
                    field=field,
                    issue_type="missing_required",
                    message=f"Required field '{field}' is missing or empty",
                    severity="error",
                )
            )

    # Pricing tier consistency
    tiers = plan_data.get("pricing_tiers", [])
    tier_prices = {t["usage_kwh"]: t["price_per_kwh"] for t in tiers}

    if not tier_prices:
        issues.append(
            ValidationIssue(
                field="pricing_tiers",
                issue_type="missing_required",
                message="No pricing tiers found",
                severity="error",
            )
        )
    else:
        # Check for tier gaps (should have at least 1000 kWh tier)
        if 1000 not in tier_prices:
            issues.append(
                ValidationIssue(
                    field="pricing_tiers",
                    issue_type="tier_gap",
                    message="Missing standard 1000 kWh pricing tier",
                    severity="warning",
                )
            )

        # Check price bounds
        for usage, price in tier_prices.items():
            if price > _PRICE_MAX_PER_KWH:
                issues.append(
                    ValidationIssue(
                        field=f"price_kwh_{usage}",
                        issue_type="out_of_range",
                        message=f"Price {price:.4f}/kWh at {usage} kWh exceeds {_PRICE_MAX_PER_KWH}/kWh",
                        severity="warning",
                    )
                )

        # Higher usage should generally have lower or equal per-kWh prices
        sorted_tiers = sorted(tier_prices.items())
        for i in range(1, len(sorted_tiers)):
            if sorted_tiers[i][1] > sorted_tiers[i - 1][1] * 1.5:
                issues.append(
                    ValidationIssue(
                        field="pricing_tiers",
                        issue_type="out_of_range",
                        message=f"Price at {sorted_tiers[i][0]} kWh ({sorted_tiers[i][1]:.4f}) is >50% higher than at {sorted_tiers[i - 1][0]} kWh ({sorted_tiers[i - 1][1]:.4f})",
                        severity="warning",
                    )
                )

    # Charge bounds
    charges = plan_data.get("charges", [])
    for charge in charges:
        if charge["charge_type"] == "base" and charge["amount"] > _BASE_CHARGE_MAX:
            issues.append(
                ValidationIssue(
                    field="base_charge_monthly",
                    issue_type="out_of_range",
                    message=f"Base charge ${charge['amount']:.2f}/month exceeds ${_BASE_CHARGE_MAX}",
                    severity="warning",
                )
            )

    # ETF bounds
    etf = plan_data.get("early_termination_fee")
    if etf is not None and etf > _ETF_MAX:
        issues.append(
            ValidationIssue(
                field="early_termination_fee",
                issue_type="out_of_range",
                message=f"ETF ${etf:.2f} exceeds ${_ETF_MAX}",
                severity="warning",
            )
        )

    return issues


def compute_confidence(plan_data: dict) -> float:
    """VAL-03: Compute confidence score based on field completeness."""
    score = 0.0

    # Check direct plan fields
    direct_fields = {
        "provider_name",
        "plan_name",
        "plan_type",
        "contract_term_months",
        "renewable_energy_pct",
    }
    for field, weight in _FIELD_WEIGHTS.items():
        if field in direct_fields:
            val = plan_data.get(field)
            if val is not None and val != "":
                score += weight

    # Check pricing tiers
    tiers = plan_data.get("pricing_tiers", [])
    tier_usages = {t["usage_kwh"] for t in tiers}
    for usage, field in [
        (500, "price_kwh_500"),
        (1000, "price_kwh_1000"),
        (2000, "price_kwh_2000"),
    ]:
        if usage in tier_usages:
            score += _FIELD_WEIGHTS.get(field, 0)

    # Check charges
    charges = plan_data.get("charges", [])
    charge_types = {c["charge_type"] for c in charges}
    charge_field_map = {
        "base": "base_charge_monthly",
        "tdu_delivery": "tdu_delivery_charge_per_kwh",
        "tdu_fixed": "tdu_fixed_charge_monthly",
    }
    for ctype, field in charge_field_map.items():
        if ctype in charge_types:
            score += _FIELD_WEIGHTS.get(field, 0)

    return round(min(score, 1.0), 2)


def validate_plan(plan_data: dict, plan_id: str) -> ValidationResult:
    """Run all validation checks and compute confidence."""
    issues = sanity_check(plan_data)
    confidence = compute_confidence(plan_data)
    needs_review = confidence < _CONFIDENCE_REVIEW_THRESHOLD or any(
        i.severity == "error" for i in issues
    )
    is_valid = not any(i.severity == "error" for i in issues)

    return ValidationResult(
        plan_id=plan_id,
        is_valid=is_valid,
        confidence_score=confidence,
        issues=issues,
        needs_review=needs_review,
    )


async def cross_validate_with_ptc(
    plan_data: dict, plan_id: str, zip_code: str = "78665"
) -> CrossValidationResult:
    """VAL-01: Cross-validate extracted prices against PTC API data."""
    result = CrossValidationResult(plan_id=plan_id)

    # Get extracted 1000 kWh price
    tiers = plan_data.get("pricing_tiers", [])
    extracted_1000 = None
    for t in tiers:
        if t["usage_kwh"] == 1000:
            extracted_1000 = t["price_per_kwh"]
            break
    result.extracted_price_1000 = extracted_1000

    try:
        payload = {
            "parameters": {
                "method": "plans",
                "zip_code": zip_code,
                "company_tdu_id": "",
                "company_unique_id": "",
                "plan_mo_from": "",
                "plan_mo_to": "",
                "estimated_use": 1000,
                "plan_type": "",
                "rating_total": "",
                "include_details": True,
                "language": 0,
                "min_usage_plan": "off",
            }
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(settings.PTC_API_URL, json=payload)
            resp.raise_for_status()
            ptc_data = resp.json()

        # Search for matching plan in PTC results
        ptc_plans = ptc_data.get("data", [])
        for ptc_plan in ptc_plans:
            if (
                str(ptc_plan.get("plan_id", "")) == plan_id
                or str(ptc_plan.get("id_key", "")) == plan_id
            ):
                ptc_price = ptc_plan.get("price_kwh1000")
                if ptc_price is not None:
                    result.ptc_price_1000 = float(ptc_price)
                    if extracted_1000 is not None:
                        diff = abs(extracted_1000 - result.ptc_price_1000)
                        result.price_diff_pct = (
                            round(diff / result.ptc_price_1000 * 100, 2)
                            if result.ptc_price_1000 > 0
                            else 0.0
                        )
                        # Allow 5% tolerance
                        result.price_match = result.price_diff_pct <= 5.0
                        if not result.price_match:
                            result.issues.append(
                                ValidationIssue(
                                    field="price_kwh_1000",
                                    issue_type="cross_validation_mismatch",
                                    message=f"Extracted price {extracted_1000:.4f} differs from PTC {result.ptc_price_1000:.4f} by {result.price_diff_pct:.1f}%",
                                    severity="warning",
                                )
                            )
                break

    except Exception as e:
        logger.warning("Cross-validation failed for plan %s: %s", plan_id, e)
        result.issues.append(
            ValidationIssue(
                field="cross_validation",
                issue_type="cross_validation_mismatch",
                message=f"Could not fetch PTC data: {e}",
                severity="warning",
            )
        )

    return result

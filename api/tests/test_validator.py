
from services.validator import compute_confidence, sanity_check, validate_plan


def _make_plan_data(**overrides):
    """Build a valid plan_data dict for testing."""
    base = {
        "provider_name": "Test Energy",
        "plan_name": "Basic Fixed 12",
        "plan_type": "fixed",
        "contract_term_months": 12,
        "early_termination_fee": 150.0,
        "renewable_energy_pct": 100.0,
        "pricing_tiers": [
            {"usage_kwh": 500, "price_per_kwh": 0.158},
            {"usage_kwh": 1000, "price_per_kwh": 0.119},
            {"usage_kwh": 2000, "price_per_kwh": 0.099},
        ],
        "charges": [
            {"charge_type": "base", "amount": 9.95, "unit": "monthly"},
            {"charge_type": "tdu_delivery", "amount": 0.04, "unit": "per_kwh"},
            {"charge_type": "tdu_fixed", "amount": 4.39, "unit": "monthly"},
        ],
    }
    base.update(overrides)
    return base


class TestSanityCheck:
    def test_valid_plan_no_issues(self):
        plan = _make_plan_data()
        issues = sanity_check(plan)
        assert len(issues) == 0

    def test_missing_provider_name(self):
        plan = _make_plan_data(provider_name="")
        issues = sanity_check(plan)
        assert any(
            i.field == "provider_name" and i.issue_type == "missing_required"
            for i in issues
        )

    def test_no_pricing_tiers(self):
        plan = _make_plan_data(pricing_tiers=[])
        issues = sanity_check(plan)
        assert any(
            i.field == "pricing_tiers" and i.issue_type == "missing_required"
            for i in issues
        )

    def test_missing_1000_tier(self):
        plan = _make_plan_data(
            pricing_tiers=[
                {"usage_kwh": 500, "price_per_kwh": 0.15},
                {"usage_kwh": 2000, "price_per_kwh": 0.10},
            ]
        )
        issues = sanity_check(plan)
        assert any(i.issue_type == "tier_gap" for i in issues)

    def test_extreme_price_flagged(self):
        plan = _make_plan_data(
            pricing_tiers=[
                {"usage_kwh": 1000, "price_per_kwh": 0.75},
            ]
        )
        issues = sanity_check(plan)
        assert any(
            i.issue_type == "out_of_range" and "1000" in i.message for i in issues
        )

    def test_extreme_base_charge_flagged(self):
        plan = _make_plan_data(
            charges=[{"charge_type": "base", "amount": 100.0, "unit": "monthly"}]
        )
        issues = sanity_check(plan)
        assert any(i.field == "base_charge_monthly" for i in issues)

    def test_extreme_etf_flagged(self):
        plan = _make_plan_data(early_termination_fee=999.0)
        issues = sanity_check(plan)
        assert any(i.field == "early_termination_fee" for i in issues)

    def test_inverted_tier_prices_flagged(self):
        plan = _make_plan_data(
            pricing_tiers=[
                {"usage_kwh": 500, "price_per_kwh": 0.05},
                {"usage_kwh": 1000, "price_per_kwh": 0.15},
            ]
        )
        issues = sanity_check(plan)
        assert any(
            i.issue_type == "out_of_range" and "higher" in i.message for i in issues
        )


class TestConfidence:
    def test_full_plan_high_confidence(self):
        plan = _make_plan_data()
        score = compute_confidence(plan)
        assert score >= 0.9

    def test_minimal_plan_low_confidence(self):
        plan = {
            "provider_name": "X",
            "plan_name": "Y",
            "plan_type": "fixed",
            "pricing_tiers": [],
            "charges": [],
        }
        score = compute_confidence(plan)
        assert score < 0.5

    def test_partial_tiers_medium_confidence(self):
        plan = _make_plan_data(
            pricing_tiers=[{"usage_kwh": 1000, "price_per_kwh": 0.12}],
            charges=[],
            contract_term_months=None,
            renewable_energy_pct=None,
        )
        score = compute_confidence(plan)
        assert 0.3 < score < 0.7


class TestValidatePlan:
    def test_valid_plan(self):
        plan = _make_plan_data()
        result = validate_plan(plan, "plan-1")
        assert result.is_valid is True
        assert result.confidence_score >= 0.9
        assert result.needs_review is False

    def test_invalid_plan_needs_review(self):
        plan = _make_plan_data(provider_name="", pricing_tiers=[])
        result = validate_plan(plan, "plan-bad")
        assert result.is_valid is False
        assert result.needs_review is True
        assert len(result.issues) >= 2

    def test_low_confidence_needs_review(self):
        plan = {
            "provider_name": "X",
            "plan_name": "Y",
            "plan_type": "fixed",
            "pricing_tiers": [],
            "charges": [],
        }
        result = validate_plan(plan, "plan-low")
        assert result.needs_review is True

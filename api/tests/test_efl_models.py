import pytest
from pydantic import ValidationError

from models.efl import EFLData


def test_efl_data_full():
    data = EFLData(
        provider_name="Test Energy",
        plan_name="Basic 12",
        plan_type="fixed",
        contract_term_months=12,
        early_termination_fee=150.0,
        etf_conditions="$150 flat fee",
        renewable_energy_pct=100.0,
        price_kwh_500=0.15,
        price_kwh_1000=0.12,
        price_kwh_2000=0.10,
        base_charge_monthly=9.95,
        tdu_delivery_charge_per_kwh=0.04,
        tdu_fixed_charge_monthly=4.39,
        minimum_usage_charge=0.0,
        minimum_usage_threshold_kwh=0,
        special_terms="$50 bill credit after 3 months",
    )
    assert data.provider_name == "Test Energy"
    assert data.plan_type == "fixed"


def test_efl_data_minimal():
    data = EFLData(
        provider_name="Min Energy",
        plan_name="Basic",
        plan_type="variable",
    )
    assert data.contract_term_months is None
    assert data.price_kwh_500 is None


def test_efl_data_invalid_plan_type():
    with pytest.raises(ValidationError):
        EFLData(
            provider_name="Bad",
            plan_name="Bad Plan",
            plan_type="indexed",
        )


def test_efl_data_negative_price():
    with pytest.raises(ValidationError):
        EFLData(
            provider_name="Bad",
            plan_name="Bad Plan",
            plan_type="fixed",
            price_kwh_500=-0.05,
        )


def test_efl_data_negative_base_charge():
    with pytest.raises(ValidationError):
        EFLData(
            provider_name="Bad",
            plan_name="Bad Plan",
            plan_type="fixed",
            base_charge_monthly=-10.0,
        )


def test_efl_data_renewable_out_of_range():
    with pytest.raises(ValidationError):
        EFLData(
            provider_name="Bad",
            plan_name="Bad Plan",
            plan_type="fixed",
            renewable_energy_pct=150.0,
        )


def test_efl_data_negative_contract_term():
    with pytest.raises(ValidationError):
        EFLData(
            provider_name="Bad",
            plan_name="Bad Plan",
            plan_type="fixed",
            contract_term_months=-1,
        )

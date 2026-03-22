import pytest

from database.connection import get_plan_data, init_db, store_efl_data
from models.efl import EFLData


SAMPLE_EFL = EFLData(
    provider_name="Test Energy",
    plan_name="Basic Fixed 12",
    plan_type="fixed",
    contract_term_months=12,
    early_termination_fee=150.0,
    etf_conditions="$150 flat fee",
    renewable_energy_pct=100.0,
    price_kwh_500=0.158,
    price_kwh_1000=0.119,
    price_kwh_2000=0.099,
    base_charge_monthly=9.95,
    tdu_delivery_charge_per_kwh=0.04,
    tdu_fixed_charge_monthly=4.39,
    minimum_usage_charge=5.0,
    minimum_usage_threshold_kwh=500,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    import asyncio

    asyncio.run(init_db())


@pytest.mark.asyncio
async def test_store_and_retrieve(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    await init_db()

    plan_rowid = await store_efl_data(
        SAMPLE_EFL, "https://example.com/efl.pdf", "plan-123"
    )
    assert plan_rowid is not None

    plan = await get_plan_data("plan-123")
    assert plan is not None
    assert plan["provider_name"] == "Test Energy"
    assert plan["plan_type"] == "fixed"
    assert plan["contract_term_months"] == 12
    assert plan["renewable_energy_pct"] == 100.0


@pytest.mark.asyncio
async def test_pricing_tiers_stored(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    await init_db()

    await store_efl_data(SAMPLE_EFL, "https://example.com/efl.pdf", "plan-456")
    plan = await get_plan_data("plan-456")

    tiers = plan["pricing_tiers"]
    assert len(tiers) == 3
    assert tiers[0]["usage_kwh"] == 500
    assert tiers[0]["price_per_kwh"] == 0.158
    assert tiers[1]["usage_kwh"] == 1000
    assert tiers[2]["usage_kwh"] == 2000


@pytest.mark.asyncio
async def test_charges_categorized(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    await init_db()

    await store_efl_data(SAMPLE_EFL, "https://example.com/efl.pdf", "plan-789")
    plan = await get_plan_data("plan-789")

    charges = plan["charges"]
    charge_types = {c["charge_type"] for c in charges}
    assert "base" in charge_types
    assert "tdu_delivery" in charge_types
    assert "tdu_fixed" in charge_types
    assert "minimum_usage" in charge_types

    base = next(c for c in charges if c["charge_type"] == "base")
    assert base["amount"] == 9.95
    assert base["unit"] == "monthly"

    tdu = next(c for c in charges if c["charge_type"] == "tdu_delivery")
    assert tdu["amount"] == 0.04
    assert tdu["unit"] == "per_kwh"


@pytest.mark.asyncio
async def test_upsert_prevents_duplicates(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    await init_db()

    await store_efl_data(SAMPLE_EFL, "https://example.com/efl.pdf", "plan-dup")

    updated = EFLData(
        provider_name="Test Energy",
        plan_name="Basic Fixed 12",
        plan_type="fixed",
        contract_term_months=24,
        price_kwh_1000=0.105,
    )
    await store_efl_data(updated, "https://example.com/efl2.pdf", "plan-dup")

    plan = await get_plan_data("plan-dup")
    assert plan["contract_term_months"] == 24

    tiers = plan["pricing_tiers"]
    assert len(tiers) == 1
    assert tiers[0]["price_per_kwh"] == 0.105


@pytest.mark.asyncio
async def test_get_plan_not_found(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    await init_db()

    result = await get_plan_data("nonexistent")
    assert result is None

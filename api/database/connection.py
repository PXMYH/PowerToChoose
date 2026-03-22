import uuid
from pathlib import Path

import aiosqlite

from config import settings

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_db():
    Path(settings.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        schema_sql = _SCHEMA_PATH.read_text()
        await db.executescript(schema_sql)
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(settings.DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def create_job(plan_id: str, efl_url: str) -> str:
    job_id = str(uuid.uuid4())
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "INSERT INTO jobs (id, plan_id, efl_url, status) VALUES (?, ?, ?, ?)",
            (job_id, plan_id, efl_url, "queued"),
        )
        await db.commit()
    return job_id


async def update_job_status(
    job_id: str,
    status: str,
    error: str | None = None,
    pdf_type: str | None = None,
):
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        await db.execute(
            """UPDATE jobs
               SET status = ?, error = COALESCE(?, error), pdf_type = COALESCE(?, pdf_type),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (status, error, pdf_type, job_id),
        )
        await db.commit()


async def update_job_extracted_data(job_id: str, extracted_data: str):
    """Store extracted EFL data JSON in the job record."""
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        await db.execute(
            """UPDATE jobs
               SET extracted_data = ?, status = 'completed',
                   updated_at = datetime('now')
               WHERE id = ?""",
            (extracted_data, job_id),
        )
        await db.commit()


async def store_efl_data(efl_data, efl_url: str, plan_id: str) -> int:
    """Store normalized EFL data in plans, pricing_tiers, and charges tables.

    Uses INSERT OR REPLACE to handle re-processing (DB-02).
    Returns the plan row ID.
    """
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        # Upsert plan record
        await db.execute(
            """INSERT INTO plans (
                   plan_id, provider_name, plan_name, plan_type,
                   contract_term_months, early_termination_fee, etf_conditions,
                   renewable_energy_pct, special_terms, efl_url
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(plan_id, provider_name, plan_name) DO UPDATE SET
                   plan_type = excluded.plan_type,
                   contract_term_months = excluded.contract_term_months,
                   early_termination_fee = excluded.early_termination_fee,
                   etf_conditions = excluded.etf_conditions,
                   renewable_energy_pct = excluded.renewable_energy_pct,
                   special_terms = excluded.special_terms,
                   efl_url = excluded.efl_url,
                   extracted_at = datetime('now')""",
            (
                plan_id,
                efl_data.provider_name,
                efl_data.plan_name,
                efl_data.plan_type,
                efl_data.contract_term_months,
                efl_data.early_termination_fee,
                efl_data.etf_conditions,
                efl_data.renewable_energy_pct,
                efl_data.special_terms,
                efl_url,
            ),
        )
        # Query the actual row ID — lastrowid returns 0 on ON CONFLICT UPDATE
        cursor = await db.execute(
            "SELECT id FROM plans WHERE plan_id = ? AND provider_name = ? AND plan_name = ?",
            (plan_id, efl_data.provider_name, efl_data.plan_name),
        )
        row = await cursor.fetchone()
        plan_rowid = row[0]

        # Clear old pricing tiers and charges for this plan (re-processing)
        await db.execute(
            "DELETE FROM pricing_tiers WHERE plan_rowid = ?", (plan_rowid,)
        )
        await db.execute("DELETE FROM charges WHERE plan_rowid = ?", (plan_rowid,))

        # Insert pricing tiers (DB-01)
        tiers = [
            (500, efl_data.price_kwh_500),
            (1000, efl_data.price_kwh_1000),
            (2000, efl_data.price_kwh_2000),
        ]
        for usage_kwh, price in tiers:
            if price is not None:
                await db.execute(
                    "INSERT INTO pricing_tiers (plan_rowid, usage_kwh, price_per_kwh) VALUES (?, ?, ?)",
                    (plan_rowid, usage_kwh, price),
                )

        # Insert categorized charges (DB-04)
        charge_entries = [
            ("base", "monthly", efl_data.base_charge_monthly, None),
            ("tdu_delivery", "per_kwh", efl_data.tdu_delivery_charge_per_kwh, None),
            ("tdu_fixed", "monthly", efl_data.tdu_fixed_charge_monthly, None),
            (
                "minimum_usage",
                "monthly",
                efl_data.minimum_usage_charge,
                efl_data.minimum_usage_threshold_kwh,
            ),
        ]
        for charge_type, unit, amount, threshold in charge_entries:
            if amount is not None:
                await db.execute(
                    "INSERT INTO charges (plan_rowid, charge_type, amount, unit, threshold_kwh) VALUES (?, ?, ?, ?, ?)",
                    (plan_rowid, charge_type, amount, unit, threshold),
                )

        await db.commit()
        return plan_rowid


async def get_plan_data(plan_id: str) -> dict | None:
    """Retrieve full plan data with pricing tiers and charges."""
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT * FROM plans WHERE plan_id = ? ORDER BY extracted_at DESC LIMIT 1",
            (plan_id,),
        )
        plan = await cursor.fetchone()
        if plan is None:
            return None
        plan_dict = dict(plan)

        cursor = await db.execute(
            "SELECT usage_kwh, price_per_kwh FROM pricing_tiers WHERE plan_rowid = ? ORDER BY usage_kwh",
            (plan_dict["id"],),
        )
        plan_dict["pricing_tiers"] = [dict(r) for r in await cursor.fetchall()]

        cursor = await db.execute(
            "SELECT charge_type, amount, unit, threshold_kwh FROM charges WHERE plan_rowid = ?",
            (plan_dict["id"],),
        )
        plan_dict["charges"] = [dict(r) for r in await cursor.fetchall()]

        return plan_dict


async def get_job(job_id: str) -> dict | None:
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

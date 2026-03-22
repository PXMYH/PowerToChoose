import asyncio
import uuid
from pathlib import Path

import libsql_experimental as libsql

from config import settings

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _get_connection():
    """Create a libsql connection — Turso if configured, local SQLite otherwise."""
    Path(settings.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    if settings.TURSO_DATABASE_URL:
        conn = libsql.connect(
            settings.DATABASE_PATH,
            sync_url=settings.TURSO_DATABASE_URL,
            auth_token=settings.TURSO_AUTH_TOKEN,
        )
        conn.sync()
        return conn
    return libsql.connect(settings.DATABASE_PATH)


def _dict_row(cursor) -> dict | None:
    """Fetch one row as dict (replaces aiosqlite.Row)."""
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def _dict_rows(cursor) -> list[dict]:
    """Fetch all rows as dicts."""
    rows = cursor.fetchall()
    if not rows:
        return []
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


def _commit_and_sync(conn):
    """Commit and sync to Turso if configured."""
    conn.commit()
    if settings.TURSO_DATABASE_URL:
        conn.sync()


def _init_db_sync():
    conn = _get_connection()
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        schema_sql = _SCHEMA_PATH.read_text()
        conn.executescript(schema_sql)
        _commit_and_sync(conn)
    finally:
        conn.close()


async def init_db():
    await asyncio.to_thread(_init_db_sync)


def _create_job_sync(plan_id: str, efl_url: str) -> str:
    job_id = str(uuid.uuid4())
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO jobs (id, plan_id, efl_url, status) VALUES (?, ?, ?, ?)",
            (job_id, plan_id, efl_url, "queued"),
        )
        _commit_and_sync(conn)
    finally:
        conn.close()
    return job_id


async def create_job(plan_id: str, efl_url: str) -> str:
    return await asyncio.to_thread(_create_job_sync, plan_id, efl_url)


def _update_job_status_sync(
    job_id: str,
    status: str,
    error: str | None = None,
    pdf_type: str | None = None,
):
    conn = _get_connection()
    try:
        conn.execute(
            """UPDATE jobs
               SET status = ?, error = COALESCE(?, error), pdf_type = COALESCE(?, pdf_type),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (status, error, pdf_type, job_id),
        )
        _commit_and_sync(conn)
    finally:
        conn.close()


async def update_job_status(
    job_id: str,
    status: str,
    error: str | None = None,
    pdf_type: str | None = None,
):
    await asyncio.to_thread(_update_job_status_sync, job_id, status, error, pdf_type)


def _update_job_extracted_data_sync(job_id: str, extracted_data: str):
    conn = _get_connection()
    try:
        conn.execute(
            """UPDATE jobs
               SET extracted_data = ?, status = 'completed',
                   updated_at = datetime('now')
               WHERE id = ?""",
            (extracted_data, job_id),
        )
        _commit_and_sync(conn)
    finally:
        conn.close()


async def update_job_extracted_data(job_id: str, extracted_data: str):
    await asyncio.to_thread(_update_job_extracted_data_sync, job_id, extracted_data)


def _store_efl_data_sync(efl_data, efl_url: str, plan_id: str) -> int:
    """Store normalized EFL data in plans, pricing_tiers, and charges tables."""
    conn = _get_connection()
    try:
        conn.execute(
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
        cursor = conn.execute(
            "SELECT id FROM plans WHERE plan_id = ? AND provider_name = ? AND plan_name = ?",
            (plan_id, efl_data.provider_name, efl_data.plan_name),
        )
        row = cursor.fetchone()
        plan_rowid = row[0]

        # Clear old pricing tiers and charges for this plan (re-processing)
        conn.execute("DELETE FROM pricing_tiers WHERE plan_rowid = ?", (plan_rowid,))
        conn.execute("DELETE FROM charges WHERE plan_rowid = ?", (plan_rowid,))

        # Insert pricing tiers
        tiers = [
            (500, efl_data.price_kwh_500),
            (1000, efl_data.price_kwh_1000),
            (2000, efl_data.price_kwh_2000),
        ]
        for usage_kwh, price in tiers:
            if price is not None:
                conn.execute(
                    "INSERT INTO pricing_tiers (plan_rowid, usage_kwh, price_per_kwh) VALUES (?, ?, ?)",
                    (plan_rowid, usage_kwh, price),
                )

        # Insert categorized charges
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
                conn.execute(
                    "INSERT INTO charges (plan_rowid, charge_type, amount, unit, threshold_kwh) VALUES (?, ?, ?, ?, ?)",
                    (plan_rowid, charge_type, amount, unit, threshold),
                )

        _commit_and_sync(conn)
        return plan_rowid
    finally:
        conn.close()


async def store_efl_data(efl_data, efl_url: str, plan_id: str) -> int:
    return await asyncio.to_thread(_store_efl_data_sync, efl_data, efl_url, plan_id)


def _get_plan_data_sync(plan_id: str) -> dict | None:
    """Retrieve full plan data with pricing tiers and charges."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM plans WHERE plan_id = ? ORDER BY extracted_at DESC LIMIT 1",
            (plan_id,),
        )
        plan_dict = _dict_row(cursor)
        if plan_dict is None:
            return None

        cursor = conn.execute(
            "SELECT usage_kwh, price_per_kwh FROM pricing_tiers WHERE plan_rowid = ? ORDER BY usage_kwh",
            (plan_dict["id"],),
        )
        plan_dict["pricing_tiers"] = _dict_rows(cursor)

        cursor = conn.execute(
            "SELECT charge_type, amount, unit, threshold_kwh FROM charges WHERE plan_rowid = ?",
            (plan_dict["id"],),
        )
        plan_dict["charges"] = _dict_rows(cursor)

        return plan_dict
    finally:
        conn.close()


async def get_plan_data(plan_id: str) -> dict | None:
    return await asyncio.to_thread(_get_plan_data_sync, plan_id)


def _get_job_sync(job_id: str) -> dict | None:
    conn = _get_connection()
    try:
        cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        return _dict_row(cursor)
    finally:
        conn.close()


async def get_job(job_id: str) -> dict | None:
    return await asyncio.to_thread(_get_job_sync, job_id)

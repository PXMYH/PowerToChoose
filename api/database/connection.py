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


async def get_job(job_id: str) -> dict | None:
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

import json
from unittest.mock import AsyncMock, patch

import pytest

from database.connection import init_db
from models.efl import DownloadResult, EFLData, PDFType, TextExtractionResult
from services.efl_extractor import ExtractionError


SAMPLE_EFL_DATA = EFLData(
    provider_name="Test Energy",
    plan_name="Basic Fixed 12",
    plan_type="fixed",
    contract_term_months=12,
    price_kwh_500=0.158,
    price_kwh_1000=0.119,
    price_kwh_2000=0.099,
    base_charge_monthly=9.95,
    tdu_delivery_charge_per_kwh=0.04,
    tdu_fixed_charge_monthly=4.39,
)

MOCK_DOWNLOAD = DownloadResult(
    url="https://example.com/efl.pdf",
    file_path="/tmp/fake.pdf",
    cached=False,
    success=True,
)

MOCK_EXTRACTION = TextExtractionResult(
    text="Electricity Facts Label\nProvider: Test Energy\nPlan: Basic Fixed 12\n" * 10,
    page_count=2,
    file_path="/tmp/fake.pdf",
    pdf_type=PDFType.text_based,
)


@pytest.mark.asyncio
async def test_pipeline_success(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    await init_db()

    from database.connection import create_job, get_job

    job_id = await create_job("plan-1", "https://example.com/efl.pdf")

    with (
        patch(
            "tasks.process_efl.download_pdf",
            new_callable=AsyncMock,
            return_value=MOCK_DOWNLOAD,
        ),
        patch("tasks.process_efl.extract_text", return_value=MOCK_EXTRACTION),
        patch(
            "tasks.process_efl.extract_efl_data",
            new_callable=AsyncMock,
            return_value=SAMPLE_EFL_DATA,
        ),
    ):
        from tasks.process_efl import process_efl_task

        await process_efl_task(job_id, "plan-1", "https://example.com/efl.pdf")

    job = await get_job(job_id)
    assert job["status"] == "completed"
    assert job["extracted_data"] is not None

    extracted = json.loads(job["extracted_data"])
    assert extracted["provider_name"] == "Test Energy"
    assert extracted["price_kwh_1000"] == 0.119


@pytest.mark.asyncio
async def test_pipeline_extraction_error(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    await init_db()

    from database.connection import create_job, get_job

    job_id = await create_job("plan-2", "https://example.com/efl.pdf")

    with (
        patch(
            "tasks.process_efl.download_pdf",
            new_callable=AsyncMock,
            return_value=MOCK_DOWNLOAD,
        ),
        patch("tasks.process_efl.extract_text", return_value=MOCK_EXTRACTION),
        patch(
            "tasks.process_efl.extract_efl_data",
            new_callable=AsyncMock,
            side_effect=ExtractionError("LLM timeout"),
        ),
    ):
        from tasks.process_efl import process_efl_task

        await process_efl_task(job_id, "plan-2", "https://example.com/efl.pdf")

    job = await get_job(job_id)
    assert job["status"] == "failed"
    assert "LLM extraction failed" in job["error"]


@pytest.mark.asyncio
async def test_pipeline_scanned_pdf(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    await init_db()

    from database.connection import create_job, get_job

    job_id = await create_job("plan-3", "https://example.com/efl.pdf")

    scanned_extraction = TextExtractionResult(
        text="",
        page_count=2,
        file_path="/tmp/fake.pdf",
        pdf_type=PDFType.scanned,
    )

    with (
        patch(
            "tasks.process_efl.download_pdf",
            new_callable=AsyncMock,
            return_value=MOCK_DOWNLOAD,
        ),
        patch("tasks.process_efl.extract_text", return_value=scanned_extraction),
    ):
        from tasks.process_efl import process_efl_task

        await process_efl_task(job_id, "plan-3", "https://example.com/efl.pdf")

    job = await get_job(job_id)
    assert job["status"] == "failed"
    assert "scanned" in job["error"]

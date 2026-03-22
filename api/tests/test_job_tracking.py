import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from database.connection import init_db
from models.efl import DownloadResult, PDFType, TextExtractionResult


@pytest.fixture(autouse=True)
def use_tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("config.settings.DATABASE_PATH", db_path)
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    monkeypatch.setattr("routers.efl.create_job", None)  # will be re-patched per test
    # Initialize the database synchronously for tests
    asyncio.run(init_db())


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    cache_dir = str(tmp_path / "cache")
    monkeypatch.setattr("config.settings.DATABASE_PATH", db_path)
    monkeypatch.setattr("config.settings.CACHE_DIR", cache_dir)
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)

    asyncio.run(init_db())

    from main import app

    return TestClient(app)


def test_process_efl_returns_202(client):
    with (
        patch("routers.efl.create_job", new_callable=AsyncMock, return_value="job-123"),
        patch("routers.efl.process_efl_task", new_callable=AsyncMock),
    ):
        resp = client.post(
            "/api/efl/process",
            json={"plan_id": "plan-1", "efl_url": "https://example.com/efl.pdf"},
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["job_id"] == "job-123"
    assert data["status"] == "queued"


def test_get_status_not_found(client):
    resp = client.get("/api/efl/status/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_job_lifecycle(tmp_path, monkeypatch):
    db_path = str(tmp_path / "lifecycle.db")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    from database.connection import create_job, get_job, update_job_status

    await init_db()

    job_id = await create_job("plan-42", "https://example.com/efl.pdf")
    job = await get_job(job_id)
    assert job["status"] == "queued"
    assert job["plan_id"] == "plan-42"

    await update_job_status(job_id, "downloading")
    job = await get_job(job_id)
    assert job["status"] == "downloading"

    await update_job_status(job_id, "failed", error="Download timeout")
    job = await get_job(job_id)
    assert job["status"] == "failed"
    assert job["error"] == "Download timeout"


@pytest.mark.asyncio
async def test_process_efl_task_success(tmp_path, monkeypatch):
    db_path = str(tmp_path / "task.db")
    cache_dir = str(tmp_path / "cache")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    monkeypatch.setattr("config.settings.CACHE_DIR", cache_dir)
    monkeypatch.setattr("services.downloader.settings.CACHE_DIR", cache_dir)
    from database.connection import create_job, get_job

    await init_db()
    job_id = await create_job("plan-99", "https://example.com/efl.pdf")

    mock_download = DownloadResult(
        url="https://example.com/efl.pdf",
        file_path="/tmp/fake.pdf",
        cached=False,
        success=True,
    )
    mock_extraction = TextExtractionResult(
        text="Electricity Facts Label content here " * 20,
        page_count=2,
        file_path="/tmp/fake.pdf",
        pdf_type=PDFType.text_based,
    )

    from models.efl import EFLData

    mock_efl_data = EFLData(
        provider_name="Test", plan_name="Test Plan", plan_type="fixed"
    )

    with (
        patch(
            "tasks.process_efl.download_pdf",
            new_callable=AsyncMock,
            return_value=mock_download,
        ),
        patch(
            "tasks.process_efl.extract_text",
            return_value=mock_extraction,
        ),
        patch(
            "tasks.process_efl.extract_efl_data",
            new_callable=AsyncMock,
            return_value=mock_efl_data,
        ),
    ):
        from tasks.process_efl import process_efl_task

        await process_efl_task(job_id, "https://example.com/efl.pdf")

    job = await get_job(job_id)
    assert job["status"] == "completed"


@pytest.mark.asyncio
async def test_process_efl_task_download_failure(tmp_path, monkeypatch):
    db_path = str(tmp_path / "fail.db")
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)
    from database.connection import create_job, get_job

    await init_db()
    job_id = await create_job("plan-fail", "https://example.com/bad.pdf")

    mock_download = DownloadResult(
        url="https://example.com/bad.pdf",
        file_path="",
        cached=False,
        success=False,
        error="404 Not Found",
    )

    with patch(
        "tasks.process_efl.download_pdf",
        new_callable=AsyncMock,
        return_value=mock_download,
    ):
        from tasks.process_efl import process_efl_task

        await process_efl_task(job_id, "https://example.com/bad.pdf")

    job = await get_job(job_id)
    assert job["status"] == "failed"
    assert "404" in job["error"]

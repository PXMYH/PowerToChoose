import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from database.connection import init_db


def test_batch_process_returns_202(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    cache_dir = str(tmp_path / "cache")
    monkeypatch.setattr("config.settings.DATABASE_PATH", db_path)
    monkeypatch.setattr("config.settings.CACHE_DIR", cache_dir)
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)

    asyncio.run(init_db())

    from main import app

    client = TestClient(app)

    with (
        patch(
            "routers.efl.create_job",
            new_callable=AsyncMock,
            side_effect=["job-1", "job-2"],
        ),
        patch("routers.efl.process_efl_task", new_callable=AsyncMock),
    ):
        resp = client.post(
            "/api/efl/process/batch",
            json={
                "plans": [
                    {"plan_id": "plan-a", "efl_url": "https://example.com/a.pdf"},
                    {"plan_id": "plan-b", "efl_url": "https://example.com/b.pdf"},
                ]
            },
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["total"] == 2
    assert len(data["jobs"]) == 2
    assert data["jobs"][0]["plan_id"] == "plan-a"
    assert data["jobs"][1]["plan_id"] == "plan-b"


def test_batch_empty_list(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    cache_dir = str(tmp_path / "cache")
    monkeypatch.setattr("config.settings.DATABASE_PATH", db_path)
    monkeypatch.setattr("config.settings.CACHE_DIR", cache_dir)
    monkeypatch.setattr("database.connection.settings.DATABASE_PATH", db_path)

    asyncio.run(init_db())

    from main import app

    client = TestClient(app)

    resp = client.post("/api/efl/process/batch", json={"plans": []})
    assert resp.status_code == 202
    data = resp.json()
    assert data["total"] == 0
    assert data["jobs"] == []

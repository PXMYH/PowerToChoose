import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from services.downloader import _url_to_cache_path, download_pdf


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("services.downloader.settings.CACHE_DIR", str(tmp_path))
    return tmp_path


@pytest.mark.asyncio
async def test_download_success(cache_dir):
    url = "https://example.com/test.pdf"
    pdf_bytes = b"%PDF-1.4 fake content"

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.content = pdf_bytes
    mock_resp.raise_for_status = lambda: None

    with patch(
        "services.downloader._download_with_retry", new_callable=AsyncMock
    ) as mock_dl:
        mock_dl.return_value = pdf_bytes
        result = await download_pdf(url)

    assert result.success is True
    assert result.cached is False
    assert result.url == url
    assert Path(result.file_path).exists()
    assert Path(result.file_path).read_bytes() == pdf_bytes


@pytest.mark.asyncio
async def test_download_cached(cache_dir):
    url = "https://example.com/cached.pdf"
    cache_path = _url_to_cache_path(url)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(b"%PDF cached")

    result = await download_pdf(url)

    assert result.success is True
    assert result.cached is True
    assert result.file_path == str(cache_path)


@pytest.mark.asyncio
async def test_download_failure(cache_dir):
    url = "https://example.com/fail.pdf"

    with patch(
        "services.downloader._download_with_retry", new_callable=AsyncMock
    ) as mock_dl:
        mock_dl.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=httpx.Request("GET", url),
            response=httpx.Response(404),
        )
        result = await download_pdf(url)

    assert result.success is False
    assert result.error is not None
    assert "404" in result.error


@pytest.mark.asyncio
async def test_cache_path_deterministic():
    url = "https://example.com/stable.pdf"
    path1 = _url_to_cache_path(url)
    path2 = _url_to_cache_path(url)
    assert path1 == path2
    expected_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    assert path1.name == f"{expected_hash}.pdf"


@pytest.mark.asyncio
async def test_download_follows_redirects(cache_dir):
    url = "https://example.com/redirect.pdf"
    pdf_bytes = b"%PDF-1.4 redirected content"

    with patch(
        "services.downloader._download_with_retry", new_callable=AsyncMock
    ) as mock_dl:
        mock_dl.return_value = pdf_bytes
        result = await download_pdf(url)

    assert result.success is True
    assert Path(result.file_path).read_bytes() == pdf_bytes

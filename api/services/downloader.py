import hashlib
import logging
from pathlib import Path

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from models.efl import DownloadResult

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


def _url_to_cache_path(url: str) -> Path:
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    return Path(settings.CACHE_DIR) / f"{url_hash}.pdf"


async def download_pdf(url: str) -> DownloadResult:
    cache_path = _url_to_cache_path(url)

    if cache_path.exists():
        return DownloadResult(
            url=url,
            file_path=str(cache_path),
            cached=True,
            success=True,
        )

    try:
        pdf_bytes = await _download_with_retry(url)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_suffix(".tmp")
        tmp_path.write_bytes(pdf_bytes)
        tmp_path.rename(cache_path)
        return DownloadResult(
            url=url,
            file_path=str(cache_path),
            cached=False,
            success=True,
        )
    except Exception as e:
        logger.error("Failed to download PDF from %s: %s", url, e)
        return DownloadResult(
            url=url,
            file_path="",
            cached=False,
            success=False,
            error=str(e),
        )


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(settings.PDF_DOWNLOAD_MAX_RETRIES),
    reraise=True,
)
async def _download_with_retry(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=settings.PDF_DOWNLOAD_TIMEOUT) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        return resp.content

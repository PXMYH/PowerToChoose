# Phase 1: PDF Processing Infrastructure - Research

**Researched:** 2026-03-21
**Domain:** PDF download, caching, text extraction, background task orchestration
**Confidence:** HIGH

## Summary

Phase 1 establishes the PDF processing pipeline foundation: downloading EFL PDFs from provider URLs (found in the `fact_sheet` field of Power to Choose API responses), caching them locally, detecting text vs scanned content, extracting text with pdfplumber, and orchestrating this as background tasks with status tracking.

The existing codebase is minimal -- a single `api/main.py` with one endpoint proxying the Power to Choose API. EFL PDFs are typically 100-200KB machine-generated documents served directly from provider domains. Some providers return PDFs from static CDN URLs, others from dynamic endpoints. All tested providers returned valid `application/pdf` content via GET requests. The `fact_sheet` field in plan data contains the direct URL.

**Primary recommendation:** Use httpx async client with tenacity retry decorator for downloads, pdfplumber for text extraction with `len(page.chars) == 0` as the scanned-image detector, FastAPI BackgroundTasks for lightweight orchestration, and an in-memory dict (upgraded to SQLite in Phase 3) for job status tracking.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PDF-01 | Download EFL PDFs with retry logic | httpx async + tenacity exponential backoff; see Download Patterns section |
| PDF-02 | Cache downloaded PDFs locally | Content-addressable storage using SHA256 of URL; see Caching Strategy section |
| PDF-03 | Detect text-based vs scanned PDFs | pdfplumber `page.chars` length check; see Classification section |
| PDF-04 | Extract text from text-based EFLs | pdfplumber `extract_text()` with layout mode; see Text Extraction section |
| PIPE-01 | Background tasks without blocking API | FastAPI BackgroundTasks; see Background Task section |
| PIPE-02 | Job status tracking | In-memory dict with enum states; see Job Tracking section |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | Async PDF downloads | Already in project; native async, streaming support, HTTP/2 |
| tenacity | 9.1.2 | Retry with backoff | De facto Python retry library; async support, exponential backoff, exception filtering |
| pdfplumber | 0.11.9 | PDF text extraction | Best-in-class for structured data/tables from machine-generated PDFs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashlib | stdlib | URL hashing for cache keys | Always -- content-addressable file naming |
| pathlib | stdlib | File path handling | Always -- cross-platform path management |
| uuid | stdlib | Job ID generation | Always -- unique job identifiers |
| enum | stdlib | Job status states | Always -- type-safe status values |
| asyncio | stdlib | Async coordination | Always -- concurrent downloads |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tenacity | Custom retry loop | tenacity handles edge cases (jitter, async, exception filtering) that hand-rolled loops miss |
| In-memory job store | Redis/SQLite | Overkill for Phase 1; Phase 3 adds SQLite persistence. In-memory is fine for single-process FastAPI |
| BackgroundTasks | Celery/ARQ | Celery needs Redis/RabbitMQ infrastructure. BackgroundTasks is sufficient for PDF processing within a single process |

**Installation:**
```bash
cd api && uv add tenacity pdfplumber
```

## Architecture Patterns

### Recommended Project Structure
```
api/
  main.py              # FastAPI app, routes
  pdf/
    __init__.py
    downloader.py      # httpx download + retry logic
    cache.py           # Local file cache management
    classifier.py      # Text vs scanned detection
    extractor.py       # pdfplumber text extraction
  pipeline/
    __init__.py
    tasks.py           # Background task orchestration
    models.py          # Job status enum, job state dataclass
```

### Pattern 1: Async PDF Download with Retry
**What:** Download PDFs using httpx async client with tenacity retry on transient failures
**When to use:** Every EFL PDF download

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pathlib import Path

RETRY_EXCEPTIONS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
)
async def download_pdf(url: str, client: httpx.AsyncClient) -> bytes:
    """Download PDF bytes from URL with retry on transient errors."""
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "pdf" not in content_type and not response.content[:5] == b"%PDF-":
        raise ValueError(f"URL did not return a PDF: {content_type}")
    return response.content
```

**Key findings from real EFL URLs:**
- Most providers return `application/pdf` content type
- Some return `application/pdf;charset=UTF-8` (with charset)
- One provider returned 405 on HEAD request but works on GET
- PDFs are typically 100-200KB (no need for streaming)
- `follow_redirects=True` is essential -- some providers redirect
- Always validate content starts with `%PDF-` as a safety check since content-type headers vary

### Pattern 2: Content-Addressable Cache
**What:** Cache PDFs using SHA256 hash of the URL as filename
**When to use:** Before every download, check cache first

```python
import hashlib
from pathlib import Path

CACHE_DIR = Path("data/pdf_cache")

def get_cache_path(url: str) -> Path:
    """Get deterministic cache path for a URL."""
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    return CACHE_DIR / f"{url_hash}.pdf"

def is_cached(url: str) -> bool:
    return get_cache_path(url).exists()

async def get_or_download(url: str, client: httpx.AsyncClient) -> Path:
    """Return cached PDF path, downloading if not cached."""
    cache_path = get_cache_path(url)
    if cache_path.exists():
        return cache_path
    pdf_bytes = await download_pdf(url, client)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(pdf_bytes)
    return cache_path
```

**Why SHA256 of URL (not content):**
- Avoids downloading to check if cached (defeats purpose)
- EFL URLs are unique per plan/product (contain product codes)
- Same URL always returns same EFL for a given point in time
- Simple to invalidate: delete file, re-download

### Pattern 3: Scanned vs Text Detection
**What:** Check if PDF has extractable text characters
**When to use:** After download, before attempting text extraction

```python
import pdfplumber

def classify_pdf(pdf_path: Path) -> str:
    """Classify PDF as 'text' or 'scanned'.

    Returns 'text' if any page has extractable characters,
    'scanned' if all pages are image-only.
    """
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if len(page.chars) > 0:
                return "text"
    return "scanned"
```

**Key insight:** pdfplumber exposes `page.chars` -- a list of character objects with position data. A page with zero chars is either blank or a scanned image. Since EFLs are never blank, zero chars means scanned. Per REQUIREMENTS out-of-scope: scanned PDFs are flagged for manual review, not OCR-processed.

### Pattern 4: Text Extraction
**What:** Extract full text from all pages of a text-based PDF
**When to use:** After classification confirms text-based PDF

```python
def extract_text(pdf_path: Path) -> str:
    """Extract text from all pages of a PDF."""
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                texts.append(text)
    return "\n\n".join(texts)
```

**Notes on pdfplumber extraction:**
- `extract_text()` returns `None` for pages with no text
- `extract_text(layout=True)` preserves spatial layout (useful if LLM needs positional context -- defer to Phase 2)
- `extract_tables()` returns structured table data -- may be useful for EFL pricing tables in Phase 2
- EFL PDFs are typically 1-3 pages

### Pattern 5: Job Status Tracking
**What:** In-memory job state management with enum statuses
**When to use:** Track background task progress

```python
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

class JobStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: int | None = None
    url: str = ""
    status: JobStatus = JobStatus.QUEUED
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

# In-memory store (sufficient for single-process FastAPI)
_jobs: dict[str, Job] = {}
```

### Pattern 6: Background Task Orchestration
**What:** FastAPI BackgroundTasks wiring the pipeline together
**When to use:** API endpoint triggers EFL processing

```python
from fastapi import BackgroundTasks

async def process_efl(job_id: str, url: str):
    """Background task: download, classify, extract."""
    job = _jobs[job_id]
    try:
        job.status = JobStatus.DOWNLOADING
        async with httpx.AsyncClient(timeout=30) as client:
            pdf_path = await get_or_download(url, client)

        job.status = JobStatus.EXTRACTING
        pdf_type = classify_pdf(pdf_path)

        if pdf_type == "scanned":
            job.status = JobStatus.COMPLETED
            # Store classification result; Phase 2 handles LLM extraction
            return

        text = extract_text(pdf_path)
        job.status = JobStatus.COMPLETED
        # Text stored for Phase 2 consumption
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error = str(e)

@app.post("/api/efl/process")
async def trigger_efl_processing(plan_id: int, fact_sheet_url: str, background_tasks: BackgroundTasks):
    job = Job(plan_id=plan_id, url=fact_sheet_url)
    _jobs[job.id] = job
    background_tasks.add_task(process_efl, job.id, fact_sheet_url)
    return {"job_id": job.id, "status": job.status}

@app.get("/api/efl/status/{job_id}")
async def get_job_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job.id, "status": job.status, "error": job.error}
```

### Anti-Patterns to Avoid
- **Downloading inside the request handler:** Always use BackgroundTasks. PDF downloads take 1-10 seconds.
- **Creating a new httpx.AsyncClient per download:** Share a client across downloads in the same background task. Client creation has overhead (connection pool setup).
- **Storing extracted text in memory:** Write to disk or database. In-memory text accumulates fast with 150+ plans.
- **Ignoring content-type validation:** Some URLs might return HTML error pages instead of PDFs. Always validate.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom retry loop | tenacity decorator | Handles jitter, async, exception types, logging; custom loops miss edge cases |
| PDF text extraction | Custom PDF parser | pdfplumber | PDF format is complex; pdfplumber handles encoding, layout, fonts correctly |
| HTTP client | urllib/requests | httpx (already in project) | Native async, streaming, HTTP/2, timeout management built-in |
| UUID generation | Random string | uuid4 | Guaranteed uniqueness, standard format, no collisions |

## Common Pitfalls

### Pitfall 1: Provider URLs That Don't Return PDFs
**What goes wrong:** Some EFL URLs return HTML login pages, redirect to homepages, or return error codes
**Why it happens:** Provider websites change, URLs expire, or require specific headers
**How to avoid:** Validate response content starts with `%PDF-` magic bytes, not just content-type header. Log and mark job as failed with descriptive error.
**Warning signs:** Content-type is `text/html`, response size is suspiciously small (< 1KB), or response doesn't start with `%PDF-`

### Pitfall 2: httpx Timeout Defaults
**What goes wrong:** Downloads hang indefinitely or timeout too aggressively
**Why it happens:** httpx default timeout is 5 seconds which is too short for some slow provider servers
**How to avoid:** Set explicit timeout: `httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))`
**Warning signs:** Frequent ConnectTimeout or ReadTimeout exceptions

### Pitfall 3: BackgroundTasks Exception Swallowing
**What goes wrong:** Background task fails silently; job status never updates to FAILED
**Why it happens:** FastAPI BackgroundTasks don't propagate exceptions to the caller. If an exception occurs before the try/except in the task, the job stays in its last status.
**How to avoid:** Wrap the entire background task in try/except, always update job status on failure. Log exceptions explicitly.
**Warning signs:** Jobs stuck in DOWNLOADING or EXTRACTING status indefinitely

### Pitfall 4: In-Memory Job Store Loses State on Restart
**What goes wrong:** Server restart clears all job status
**Why it happens:** Dict is in-process memory only
**How to avoid:** Accept this limitation for Phase 1. Phase 3 adds SQLite persistence. Document this as a known limitation.
**Warning signs:** N/A -- expected behavior, just document it

### Pitfall 5: pdfplumber Failing on Encrypted/Protected PDFs
**What goes wrong:** `pdfplumber.open()` raises exception on password-protected PDFs
**Why it happens:** Some providers may protect their EFL PDFs
**How to avoid:** Catch the exception, mark the PDF as "protected" classification alongside "text" and "scanned"
**Warning signs:** `pdfplumber.pdfminer.pdfparser.PDFSyntaxError` or similar on open

### Pitfall 6: Race Condition on Cache Writes
**What goes wrong:** Two concurrent tasks download the same PDF and write to the same cache path
**Why it happens:** Concurrent background tasks processing plans from the same provider
**How to avoid:** Write to a temp file first, then atomic rename via `Path.replace()`. Or use an asyncio Lock per URL.
**Warning signs:** Corrupted PDF files in cache

## Code Examples

### Complete Downloader Module
```python
# api/pdf/downloader.py
import httpx
from pathlib import Path
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

logger = logging.getLogger(__name__)

RETRY_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.PoolTimeout,
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def download_pdf(url: str, client: httpx.AsyncClient) -> bytes:
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()

    # Validate it's actually a PDF
    if not response.content[:5] == b"%PDF-":
        content_type = response.headers.get("content-type", "unknown")
        raise ValueError(
            f"Expected PDF but got {content_type} "
            f"(first bytes: {response.content[:20]})"
        )
    return response.content
```

### Complete Classifier Module
```python
# api/pdf/classifier.py
import pdfplumber
from pathlib import Path
from enum import Enum

class PDFType(str, Enum):
    TEXT = "text"
    SCANNED = "scanned"
    PROTECTED = "protected"
    INVALID = "invalid"

def classify_pdf(pdf_path: Path) -> PDFType:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return PDFType.INVALID
            for page in pdf.pages:
                if len(page.chars) > 0:
                    return PDFType.TEXT
            return PDFType.SCANNED
    except Exception:
        return PDFType.PROTECTED  # or INVALID -- log for investigation
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyPDF2 | pypdf (renamed) | 2022 | PyPDF2 is deprecated; use pypdf if needed as fallback |
| requests + threading | httpx async | 2020+ | Native async eliminates thread pool complexity for concurrent downloads |
| Manual PDF parsing | pdfplumber | Stable since 2019 | Purpose-built for structured extraction; handles edge cases |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none -- Wave 0 must create |
| Quick run command | `cd api && python -m pytest tests/ -x -q` |
| Full suite command | `cd api && python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PDF-01 | Download PDF with retry on failure | unit (mock httpx) | `pytest tests/test_downloader.py -x` | Wave 0 |
| PDF-02 | Cache hit skips download | unit | `pytest tests/test_cache.py -x` | Wave 0 |
| PDF-03 | Detect text vs scanned PDF | unit (fixture PDFs) | `pytest tests/test_classifier.py -x` | Wave 0 |
| PDF-04 | Extract text from text PDF | unit (fixture PDF) | `pytest tests/test_extractor.py -x` | Wave 0 |
| PIPE-01 | Background task runs without blocking | integration (TestClient) | `pytest tests/test_pipeline.py -x` | Wave 0 |
| PIPE-02 | Job status transitions correctly | unit | `pytest tests/test_pipeline.py::test_job_status -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd api && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd api && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `api/tests/__init__.py` -- test package
- [ ] `api/tests/conftest.py` -- shared fixtures (sample PDF bytes, mock client)
- [ ] `api/tests/fixtures/` -- directory with sample text PDF and scanned PDF for testing
- [ ] `api/pyproject.toml` -- add pytest to dev dependencies
- [ ] pytest install: `cd api && uv add --dev pytest pytest-asyncio httpx[testing]`

## Open Questions

1. **EFL URL Stability**
   - What we know: URLs contain product codes and appear stable for the plan's lifetime
   - What's unclear: Do URLs change when plans are updated? Do old URLs stop working?
   - Recommendation: Cache aggressively, implement cache invalidation by age (e.g., re-download after 7 days)

2. **Concurrent Download Limits**
   - What we know: 151 plans returned for one zip code; each has an EFL URL
   - What's unclear: Will providers rate-limit or block rapid concurrent requests?
   - Recommendation: Use `asyncio.Semaphore(5)` to limit concurrent downloads per provider domain. Start conservative.

3. **Extracted Text Storage Before Phase 3**
   - What we know: Phase 3 adds SQLite; Phase 1 only needs to extract text
   - What's unclear: Where should extracted text live between Phase 1 and Phase 3?
   - Recommendation: Store alongside cached PDF as `.txt` file in same cache directory. Simple, no DB needed yet.

## Sources

### Primary (HIGH confidence)
- httpx official docs (python-httpx.org) -- timeout, streaming, transport retries
- pdfplumber GitHub README -- API for open, chars, extract_text, extract_tables
- FastAPI official docs -- BackgroundTasks usage, limitations, Celery comparison
- tenacity official docs -- retry decorator, exponential backoff, async support
- Live Power to Choose API -- tested actual EFL URLs from 5 providers

### Secondary (MEDIUM confidence)
- httpx transport retry docs -- confirms only ConnectError/ConnectTimeout retried by built-in; tenacity needed for broader retry

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified via official docs and already partially in use
- Architecture: HIGH -- patterns derived from official docs and tested against real EFL data
- Pitfalls: HIGH -- identified through testing real provider URLs and reading library documentation
- Validation: MEDIUM -- test structure is standard but fixture PDFs need to be sourced

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable libraries, unlikely to change)

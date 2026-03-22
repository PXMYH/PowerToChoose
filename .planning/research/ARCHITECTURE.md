# Architecture Research

**Domain:** PDF Document Processing Pipeline (Download → LLM Extraction → Storage)
**Researched:** 2026-03-21
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
│  │  Trigger  │  │  Status   │  │  Results  │  │  Existing │    │
│  │ Endpoint  │  │ Endpoint  │  │ Endpoint  │  │  /plans   │    │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘    │
│        │              │              │              │            │
├────────┴──────────────┴──────────────┴──────────────┴────────────┤
│                    Processing Layer                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Background Task Queue                        │   │
│  │  (FastAPI BackgroundTasks / arq / RQ)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│        │                    │                    │               │
│  ┌─────▼──────┐      ┌──────▼───────┐    ┌──────▼───────┐      │
│  │   PDF      │      │   LLM        │    │   Parser     │      │
│  │ Downloader │ ───> │  Extractor   │───>│  (Structured)│      │
│  └────────────┘      └──────────────┘    └──────┬───────┘      │
│                                                   │              │
├───────────────────────────────────────────────────┴──────────────┤
│                    Storage Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   SQLite     │  │  File Cache  │  │   Metadata   │          │
│  │   (aiosqlite)│  │  (PDFs)      │  │   Store      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Trigger Endpoint** | Accept EFL parsing requests, validate input, enqueue job | FastAPI route handler with BackgroundTasks or task queue client |
| **Status Endpoint** | Query job progress/status | FastAPI route reading from status store (SQLite or Redis) |
| **Results Endpoint** | Fetch parsed EFL data | FastAPI route querying SQLite for structured results |
| **PDF Downloader** | Fetch PDF from provider URL, handle retries, cache locally | httpx.AsyncClient with retry logic, save to temp/cache directory |
| **LLM Extractor** | Convert PDF to images, send to LLM API, receive structured text | PyMuPDF for PDF→image + LiteLLM for OpenRouter API calls |
| **Parser** | Transform LLM output into structured schema, validate | Pydantic models for validation + custom parsing logic |
| **SQLite Storage** | Store parsed EFL data with ACID guarantees | aiosqlite with explicit transaction control |
| **File Cache** | Store downloaded PDFs to avoid re-downloading | Local filesystem with TTL-based cleanup |
| **Metadata Store** | Track processing status, errors, timestamps | SQLite table for job tracking |

## Recommended Project Structure

```
api/
├── main.py                   # FastAPI app entry point
├── routers/
│   ├── plans.py             # Existing Power to Choose plans endpoint
│   └── efl.py               # NEW: EFL parsing endpoints (trigger, status, results)
├── services/
│   ├── downloader.py        # NEW: PDF download logic with httpx
│   ├── extractor.py         # NEW: LLM extraction via LiteLLM
│   └── parser.py            # NEW: Structured data parsing + validation
├── models/
│   ├── efl_schema.py        # NEW: Pydantic models for EFL data
│   └── job_status.py        # NEW: Job tracking models
├── database/
│   ├── connection.py        # NEW: aiosqlite connection management
│   ├── schema.sql           # NEW: SQLite schema for EFL data + job tracking
│   └── queries.py           # NEW: Database query functions
├── tasks/
│   └── process_efl.py       # NEW: Background task orchestration
├── config.py                # NEW: Environment variables (OpenRouter API key, etc.)
└── utils/
    ├── retry.py             # NEW: Retry logic for PDF downloads
    └── cache.py             # NEW: File cache management

data/
├── cache/                   # NEW: Cached PDF files
└── power2choose.db          # NEW: SQLite database
```

### Structure Rationale

- **routers/:** Separates EFL pipeline endpoints from existing plan listing logic; allows independent evolution
- **services/:** Each stage of the pipeline (download, extract, parse) is a discrete service with single responsibility
- **models/:** Pydantic schemas enforce structured data contracts between pipeline stages
- **database/:** Centralizes all SQLite interaction; schema.sql documents DB structure explicitly
- **tasks/:** Background processing logic isolated from HTTP layer; easy to switch from BackgroundTasks to arq/RQ later
- **data/:** External from codebase for easy gitignore and backup

## Architectural Patterns

### Pattern 1: Task Queue with Status Polling

**What:** API accepts job request, returns job ID immediately (202 Accepted), client polls status endpoint until completion.

**When to use:** Long-running operations (PDF download + LLM extraction can take 10-60 seconds per document).

**Trade-offs:**
- ✅ Non-blocking: API remains responsive
- ✅ Simple: No WebSockets or Server-Sent Events
- ✅ Reliable: Jobs survive server restarts (with persistent queue)
- ❌ Polling overhead: Clients make repeated requests
- ❌ Latency: Client doesn't know immediately when job completes

**Example:**
```python
# routers/efl.py
@router.post("/efl/process", status_code=202)
async def trigger_efl_processing(
    plan_id: str,
    efl_url: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    job_id = str(uuid.uuid4())

    # Store initial job status
    await db.execute(
        "INSERT INTO job_status (job_id, status, plan_id, efl_url) VALUES (?, ?, ?, ?)",
        (job_id, "queued", plan_id, efl_url),
    )
    await db.commit()

    # Enqueue processing task
    background_tasks.add_task(process_efl_pipeline, job_id, plan_id, efl_url)

    return {"job_id": job_id, "status": "queued"}

@router.get("/efl/status/{job_id}")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        "SELECT status, progress, error FROM job_status WHERE job_id = ?",
        (job_id,),
    )
    row = await result.fetchone()
    if not row:
        raise HTTPException(404, "Job not found")

    return {"job_id": job_id, "status": row[0], "progress": row[1], "error": row[2]}
```

### Pattern 2: Pipeline with Fail-Fast Error Handling

**What:** Each pipeline stage validates inputs/outputs and fails immediately on error rather than continuing with bad data.

**When to use:** Multi-stage processing where downstream stages depend on upstream quality (bad PDF → bad extraction → corrupt data).

**Trade-offs:**
- ✅ Data integrity: Prevents cascade of errors
- ✅ Clear errors: Failures are localized and traceable
- ✅ Debuggable: Each stage logs its inputs/outputs
- ❌ No partial results: Entire job fails if any stage fails
- ❌ Retry complexity: Must decide retry strategy per-stage

**Example:**
```python
# tasks/process_efl.py
async def process_efl_pipeline(job_id: str, plan_id: str, efl_url: str):
    try:
        # Stage 1: Download PDF
        await update_job_status(job_id, "downloading", progress=10)
        pdf_path = await download_pdf(efl_url)
        if not pdf_path.exists():
            raise PipelineError("PDF download failed")

        # Stage 2: Extract with LLM
        await update_job_status(job_id, "extracting", progress=40)
        raw_text = await extract_with_llm(pdf_path)
        if not raw_text or len(raw_text) < 100:
            raise PipelineError("LLM extraction returned insufficient data")

        # Stage 3: Parse into structured data
        await update_job_status(job_id, "parsing", progress=70)
        parsed_data = parse_efl_data(raw_text)
        if not parsed_data.validate():
            raise PipelineError("Parsed data failed validation")

        # Stage 4: Store in database
        await update_job_status(job_id, "storing", progress=90)
        await store_efl_data(plan_id, parsed_data)

        await update_job_status(job_id, "completed", progress=100)

    except PipelineError as e:
        await update_job_status(job_id, "failed", error=str(e))
        raise
```

### Pattern 3: Async Context Managers for Resource Cleanup

**What:** Use async context managers to ensure database connections, HTTP clients, and file handles are properly cleaned up even when errors occur.

**When to use:** Always — especially critical in async code where resources can leak across coroutines.

**Trade-offs:**
- ✅ Guaranteed cleanup: Resources released even on exception
- ✅ Clear lifetime: Scope of resource usage is explicit
- ✅ Async-safe: Works correctly with asyncio
- ❌ Verbosity: More lines of code than raw open/close

**Example:**
```python
# services/downloader.py
async def download_pdf(url: str) -> Path:
    cache_path = get_cache_path(url)

    # Check cache first
    if cache_path.exists():
        return cache_path

    # Download with automatic client cleanup
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(cache_path, "wb") as f:
            await f.write(response.content)

    return cache_path

# database/connection.py
@asynccontextmanager
async def get_db_session():
    db = await aiosqlite.connect("data/power2choose.db")
    try:
        yield db
    finally:
        await db.close()
```

## Data Flow

### Request Flow (EFL Processing)

```
[Client Request: POST /efl/process]
    ↓
[API Endpoint] → [Generate Job ID] → [Store Job Record (status=queued)]
    ↓
[Return 202 + Job ID]
    │
    └─────[Background Task Enqueued]
              ↓
        [PDF Downloader] → [Download from Provider URL] → [Cache to disk]
              ↓
        [LLM Extractor] → [Convert PDF→Images] → [Call OpenRouter API]
              ↓                                         ↓
        [Parser] ← [Receive Structured Text] ← [nvidia/nemotron]
              ↓
        [Validate with Pydantic] → [Store in SQLite]
              ↓
        [Update Job Status (status=completed)]


[Client Polling: GET /efl/status/{job_id}]
    ↓
[Status Endpoint] → [Query job_status table] → [Return status/progress/error]
```

### State Transitions (Job Status)

```
queued → downloading → extracting → parsing → storing → completed
                ↓          ↓           ↓         ↓
              failed    failed      failed    failed
```

### Key Data Flows

1. **Job lifecycle tracking:** Job record created immediately on request → updated at each pipeline stage → final status persisted for client retrieval
2. **PDF caching:** Check cache before downloading → if hit, skip to extraction → if miss, download and cache with TTL
3. **LLM extraction:** PDF bytes → PyMuPDF renders to images → images encoded as base64 → sent to LiteLLM → LiteLLM calls OpenRouter → structured JSON response
4. **Error propagation:** Any stage failure → update job status to "failed" with error message → halt pipeline → client sees failure on next poll

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **1-100 plans** | FastAPI BackgroundTasks sufficient; single-file SQLite; no external queue |
| **100-10k plans** | Add arq (Redis-based async queue) for better job management; consider rate limiting LLM API calls; add PDF cache cleanup job |
| **10k+ plans** | Switch to PostgreSQL for concurrent writes; use Celery with multiple workers; implement batch processing; add CDN for PDF caching |

### Scaling Priorities

1. **First bottleneck: LLM API rate limits**
   - OpenRouter free tier has rate limits
   - **Fix:** Add exponential backoff + retry logic; queue depth limiting; upgrade to paid tier if needed

2. **Second bottleneck: SQLite write concurrency**
   - SQLite locks entire database on write; concurrent jobs will block
   - **Fix:** Use WAL mode (`PRAGMA journal_mode=WAL`) for better concurrency; batch inserts; consider PostgreSQL if >10 concurrent writers

3. **Third bottleneck: PDF download time**
   - Some provider PDFs are slow to download (5-10s)
   - **Fix:** Increase httpx timeout; implement parallel downloads with semaphore limiting; cache aggressively

## Anti-Patterns

### Anti-Pattern 1: Blocking Database Calls in Async Handlers

**What people do:** Use `sqlite3` directly in FastAPI routes without thread pool
```python
# ❌ WRONG: Blocks event loop
import sqlite3
@app.get("/results")
async def get_results():
    conn = sqlite3.connect("db.sqlite")  # BLOCKS!
    return conn.execute("SELECT * FROM efl_data").fetchall()
```

**Why it's wrong:** `sqlite3` is synchronous and will block the entire FastAPI event loop, making the API unresponsive during queries.

**Do this instead:** Use `aiosqlite` for async database operations
```python
# ✅ CORRECT: Non-blocking
import aiosqlite
@app.get("/results")
async def get_results():
    async with aiosqlite.connect("db.sqlite") as db:
        async with db.execute("SELECT * FROM efl_data") as cursor:
            return await cursor.fetchall()
```

### Anti-Pattern 2: Storing Binary PDFs in SQLite as BLOBs

**What people do:** Store entire PDF files in SQLite BLOB columns
```python
# ❌ WRONG: Bloats database
await db.execute(
    "INSERT INTO efl_data (plan_id, pdf_content) VALUES (?, ?)",
    (plan_id, pdf_bytes)  # Large binary data
)
```

**Why it's wrong:**
- SQLite file size grows rapidly (PDFs are 500KB-5MB each)
- Slows down queries and backups
- No benefit over filesystem storage

**Do this instead:** Store PDFs on filesystem, reference by path
```python
# ✅ CORRECT: Store path reference only
cache_path = f"data/cache/{plan_id}.pdf"
Path(cache_path).write_bytes(pdf_bytes)

await db.execute(
    "INSERT INTO efl_data (plan_id, pdf_path, extracted_at) VALUES (?, ?, ?)",
    (plan_id, cache_path, datetime.now())
)
```

### Anti-Pattern 3: Running Long Tasks in BackgroundTasks for Production

**What people do:** Use FastAPI's `BackgroundTasks` for all async work and ship to production
```python
# ⚠️ ACCEPTABLE FOR MVP, BAD FOR PRODUCTION
@app.post("/process")
async def process(background_tasks: BackgroundTasks):
    background_tasks.add_task(long_running_job)
    return {"status": "processing"}
```

**Why it's wrong:**
- Tasks die if server restarts (no persistence)
- No retry mechanism
- No visibility into queue depth or failures
- Tasks run in same process as API (resource contention)

**Do this instead:** Use a proper task queue for production
```python
# ✅ CORRECT: Use arq or Celery
from arq import create_pool
from arq.connections import RedisSettings

@app.post("/process")
async def process(redis: ArqRedis = Depends(get_redis_pool)):
    job = await redis.enqueue_job("process_efl", plan_id, efl_url)
    return {"job_id": job.job_id, "status": "queued"}
```

**Pragmatic approach:** Start with `BackgroundTasks` for MVP/prototype, migrate to arq/RQ when you need reliability.

### Anti-Pattern 4: Not Handling LLM API Failures Gracefully

**What people do:** Assume LLM API always succeeds
```python
# ❌ WRONG: No error handling
response = await client.chat.completions.create(
    model="nvidia/nemotron-...",
    messages=[{"role": "user", "content": prompt}]
)
return response.choices[0].message.content
```

**Why it's wrong:**
- LLM APIs have rate limits (return 429)
- Network issues cause timeouts
- Model unavailability (OpenRouter returns 503)
- Malformed responses (no choices returned)

**Do this instead:** Wrap LLM calls with retry logic and validation
```python
# ✅ CORRECT: Defensive LLM calls
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=60),
    reraise=True
)
async def extract_with_llm(pdf_path: Path) -> str:
    try:
        response = await client.chat.completions.create(
            model="nvidia/nemotron-...",
            messages=[{"role": "user", "content": prompt}],
            timeout=120.0
        )

        if not response.choices:
            raise ExtractionError("LLM returned no choices")

        content = response.choices[0].message.content
        if not content or len(content) < 50:
            raise ExtractionError("LLM returned insufficient content")

        return content

    except OpenRouterError as e:
        logger.error(f"OpenRouter API error: {e}")
        raise ExtractionError(f"LLM API failed: {e}")
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **OpenRouter API** | HTTP via LiteLLM client | Requires API key in env var `OPENROUTER_API_KEY`; free tier rate limited; use exponential backoff |
| **Power to Choose API** | HTTP via httpx (existing) | Already integrated in `main.py`; EFL URLs come from plan listings |
| **Provider PDF URLs** | Direct HTTP download via httpx | URLs in plan data; vary by provider; some require `User-Agent` header; implement caching |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **API ↔ Task Queue** | Job ID via database | API writes job record → task reads it; status updates flow back via DB |
| **Downloader ↔ Extractor** | File path via return value | Downloader saves PDF → returns Path → Extractor reads Path |
| **Extractor ↔ Parser** | Raw text string | Extractor returns unstructured text → Parser applies schema |
| **Parser ↔ Database** | Pydantic models | Parser outputs validated models → Database layer serializes to SQL |
| **Existing /plans ↔ New /efl** | Shared database | Both read from same SQLite DB; /plans can optionally JOIN with efl_data table |

### Suggested Build Order (Dependencies)

1. **Database schema + aiosqlite connection** (foundation for everything)
2. **PDF Downloader service** (independent, testable with any URL)
3. **LLM Extractor service** (depends on downloader for PDF inputs)
4. **Parser + Pydantic models** (depends on extractor for raw text)
5. **Background task orchestration** (wires together services 2-4)
6. **API endpoints** (trigger, status, results — depends on task layer)
7. **Integration with existing /plans** (optional enhancement)

## Sources

**Architecture Research:**
- FastAPI Background Tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/ (MEDIUM confidence — official docs, but basic pattern)
- FastAPI Async Testing: https://fastapi.tiangolo.com/advanced/async-tests/ (HIGH confidence — official docs)
- Python sqlite3 async patterns: https://docs.python.org/3/library/sqlite3.html (HIGH confidence — official docs, but generic)

**Library Integration:**
- LiteLLM docs: https://docs.litellm.ai/docs/ (MEDIUM confidence — official but high-level)
- LiteLLM vision API: https://docs.litellm.ai/docs/completion/vision (MEDIUM confidence — confirms multimodal support)
- OpenRouter docs: https://openrouter.ai/docs (MEDIUM confidence — confirms OpenAI-compatible API)
- PyMuPDF docs: https://pymupdf.readthedocs.io/en/latest/ (HIGH confidence — comprehensive PDF→image capabilities documented)
- pypdf docs: https://pypdf.readthedocs.io/en/stable/ (MEDIUM confidence — text extraction only, limited for scanned PDFs)

**Task Queue Options:**
- Celery architecture: https://github.com/celery/celery (MEDIUM confidence — established but heavyweight)
- RQ architecture: https://python-rq.org/ (MEDIUM confidence — simpler alternative)
- arq architecture: https://arq-docs.helpmanual.io/ (HIGH confidence — built for asyncio, best fit for FastAPI)

**Confidence Assessment:**
- **Overall: HIGH** — Core patterns (async FastAPI, SQLite, PDF processing, LLM APIs) are well-documented
- **Pipeline architecture:** Standard pattern, no surprises
- **Scaling guidance:** Based on common bottlenecks in document processing systems
- **Anti-patterns:** Derived from async Python best practices and FastAPI patterns

---
*Architecture research for: Power to Choose EFL Parser*
*Researched: 2026-03-21*

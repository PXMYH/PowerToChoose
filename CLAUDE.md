<!-- GSD:project-start source:PROJECT.md -->
## Project

**Power to Choose - EFL Parser**

A document processing pipeline that downloads Electricity Facts Labels (EFLs) and Terms of Service PDFs from Texas electricity providers, extracts structured data using LLM-powered OCR via OpenRouter, and stores the results in a SQLite database for analysis, insights, and simulation.

**Core Value:** Accurately extract and store structured pricing, charges, and contract details from EFL PDFs so users can make informed electricity plan comparisons beyond what the Power to Choose website provides.

### Constraints

- **LLM Provider**: Must use OpenRouter with nvidia/nemotron model via LiteLLM library
- **Storage**: SQLite database for simplicity and portability
- **Backend**: Python (existing FastAPI backend)
- **Cost**: Use free-tier model to minimize API costs
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Framework (Already Established)
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | 0.135.1 | Backend API framework | Already in use; modern async web framework with excellent performance and type safety |
| Python | 3.10+ | Language | Required by FastAPI and all modern Python libraries; 3.10+ enables best type hint support |
### PDF Processing
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pdfplumber | 0.11.9 | Primary PDF text extraction | **Best for structured data extraction** — excellent table detection, detailed object access with coordinates, visual debugging tools. Built on pdfminer.six. Works best on machine-generated PDFs (which EFLs typically are). |
| pypdf | 6.9.1 | Fallback for simple PDFs | Lightweight pure-Python library with zero dependencies. Use when pdfplumber overkills or for PDF metadata extraction. Good for quick text-only extraction from well-formed PDFs. |
| PyMuPDF (fitz) | 1.27.2.2 | Alternative for performance-critical cases | High-performance C-based library with minimal dependencies. Consider if pdfplumber is too slow on large batches. Supports broader format range (XPS, eBooks). |
### HTTP Client
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| httpx | 0.28.1 | PDF download client | Modern HTTP client with both sync and async support, HTTP/2, type annotations. Requests-compatible API but with better async capabilities for concurrent PDF downloads. Required for efficient batch downloading. |
### LLM Integration
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| LiteLLM | 1.82.5 | OpenRouter API client | Unified interface to 100+ LLMs including OpenRouter. Handles retries, fallbacks, consistent output format. Use `model="openrouter/<model-name>"` format. Supports streaming and structured outputs. |
| instructor | 1.14.5 | Structured LLM output extraction | **Essential for reliability** — enforces Pydantic models on LLM responses with automatic validation, retry logic, and streaming support. Eliminates manual JSON parsing. Works seamlessly with LiteLLM/OpenRouter. 3M+ monthly downloads, production-proven. |
| Pydantic | 2.12.5 | Data validation and parsing | Type-safe data models for parsed EFL data. v2.x provides major performance improvements and better validation. Required by instructor and FastAPI. |
### Data Storage
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| sqlite3 | Built-in (stdlib) | SQLite database interface | No external installation required. Sufficient for single-file database with straightforward queries. Use Python's built-in module unless ORM benefits outweigh complexity. |
### Configuration Management
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pydantic-settings | 2.13.1 | Environment variable management | Type-safe settings with automatic validation. Integrates perfectly with Pydantic models. Supports .env files, cloud secret managers (AWS/Azure/GCP), YAML/TOML configs. Production-stable. |
| python-dotenv | 1.2.2 | .env file loading | Simple, focused library for loading .env files. Use with pydantic-settings for local development. 12-factor app pattern. |
### Testing
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pytest | 9.0.2 | Testing framework | Python's de facto standard testing framework. Simple assert-based syntax, auto-discovery, fixture system, 1300+ plugins. Essential for testing PDF parsing accuracy, LLM integration, database operations. |
## Supporting Libraries (Optional/Conditional)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pdf2image | 1.17.0 | Convert PDF pages to images | Only if encountering scanned/image-based PDFs that pdfplumber can't extract. Requires poppler system dependency. |
| pytesseract | 0.3.13 | OCR for scanned PDFs | Only for scanned documents where PDF text extraction fails. Wrapper around Google's Tesseract-OCR. Most EFLs are machine-generated, so OCR should rarely be needed. |
| Pillow | 12.1.1 | Image processing | Required if using pdf2image or pytesseract. Mature, foundational Python imaging library. |
## Installation
### Core Dependencies
# PDF processing
# HTTP client
# LLM integration
# Configuration
### Development Dependencies
### Optional (Add if needed)
# For scanned PDFs (requires poppler system dependency)
### Environment Setup
# .env file
## Alternatives Considered
| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| PDF extraction | pdfplumber | PyMuPDF (fitz) | PyMuPDF is faster but less specialized for structured data/tables. pdfplumber's table extraction is superior for EFL documents. Use PyMuPDF only if performance becomes bottleneck. |
| PDF extraction | pdfplumber | pytesseract + pdf2image | OCR is overkill for machine-generated PDFs and much slower. Use only for scanned documents. Most EFLs are digital. |
| HTTP client | httpx | requests | requests lacks async support needed for concurrent PDF downloads. httpx provides same API with async capabilities. |
| LLM wrapper | LiteLLM | OpenAI SDK | OpenAI SDK only supports OpenAI. LiteLLM provides unified interface to OpenRouter and 100+ other providers. Essential for provider flexibility. |
| Structured output | instructor | Manual JSON parsing | instructor handles validation, retries, streaming automatically. Manual parsing is error-prone and requires custom retry logic. instructor is production-proven (3M+ downloads/month). |
| Database | sqlite3 (stdlib) | SQLAlchemy | SQLAlchemy adds ORM overhead unnecessary for straightforward insert/query patterns. Use stdlib unless needing ORM features or multi-database support. |
| Settings | pydantic-settings | os.environ | pydantic-settings provides type validation, .env support, structured config. os.environ returns only strings without validation. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| PyPDF2 (old name) | Deprecated, renamed to pypdf in 2022 | pypdf 6.9.1 |
| requests for async downloads | No async support, blocks on I/O | httpx 0.28.1 |
| Manual JSON parsing of LLM outputs | Error-prone, no validation, requires custom retry logic | instructor 1.14.5 with Pydantic models |
| Langchain for simple LLM calls | Heavy dependency, unnecessary abstraction for single-purpose parsing | LiteLLM + instructor (lightweight, focused) |
| configparser or manual .env parsing | No type validation, string-only values | pydantic-settings 2.13.1 |
| unittest (stdlib) | Verbose API (self.assertEqual), limited features | pytest 9.0.2 (simpler, more powerful) |
## Stack Patterns
### Pattern 1: PDF Text Extraction Pipeline
### Pattern 2: Structured LLM Output with Instructor
# Define structured output model
# Patch LiteLLM with instructor
# Extract structured data
# charges is now a validated EFLCharges instance
### Pattern 3: Type-Safe Configuration
# Load settings (reads .env automatically)
### Pattern 4: Async PDF Download
## Version Compatibility
| Package | Requires | Notes |
|---------|----------|-------|
| FastAPI 0.135.1 | Python 3.10+ | Already in project |
| pdfplumber 0.11.9 | Python 3.8+ | Compatible with FastAPI environment |
| instructor 1.14.5 | Pydantic 2.x | Requires Pydantic v2, not v1 |
| pydantic 2.12.5 | Python 3.9+ | FastAPI requires Pydantic v2 |
| pydantic-settings 2.13.1 | Pydantic 2.x | Must match Pydantic major version |
| LiteLLM 1.82.5 | Python 3.8+ | Works with all listed dependencies |
| httpx 0.28.1 | Python 3.8+ | Compatible with async FastAPI routes |
| pytest 9.0.2 | Python 3.10+ | Matches project Python version |
## Sources
- LiteLLM 1.82.5 — [PyPI](https://pypi.org/project/litellm/), [Official Docs - OpenRouter Integration](https://docs.litellm.ai/docs/providers/openrouter)
- pdfplumber 0.11.9 — [PyPI](https://pypi.org/project/pdfplumber/)
- pypdf 6.9.1 — [PyPI](https://pypi.org/project/pypdf/), [GitHub](https://github.com/py-pdf/pypdf)
- PyMuPDF 1.27.2.2 — [PyPI](https://pypi.org/project/pymupdf/)
- httpx 0.28.1 — [PyPI](https://pypi.org/project/httpx/)
- instructor 1.14.5 — [PyPI](https://pypi.org/project/instructor/)
- Pydantic 2.12.5 — [PyPI](https://pypi.org/project/pydantic/)
- pydantic-settings 2.13.1 — [PyPI](https://pypi.org/project/pydantic-settings/)
- python-dotenv 1.2.2 — [PyPI](https://pypi.org/project/python-dotenv/)
- pytest 9.0.2 — [PyPI](https://pypi.org/project/pytest/)
- FastAPI 0.135.1 — [PyPI](https://pypi.org/project/fastapi/)
- sqlite3 — [Python stdlib docs](https://docs.python.org/3/library/sqlite3.html)
- pdf2image 1.17.0 — [PyPI](https://pypi.org/project/pdf2image/)
- pytesseract 0.3.13 — [PyPI](https://pypi.org/project/pytesseract/)
- Pillow 12.1.1 — [PyPI](https://pypi.org/project/pillow/)
- OpenRouter model availability (nvidia/nemotron) — Could not verify current free models from OpenRouter website. Recommend checking [openrouter.ai/models](https://openrouter.ai/models) directly for current pricing/availability.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

- **Config**: All settings via `config.py` (pydantic-settings). Access as `from config import settings`.
- **Routers**: Each domain gets its own file in `routers/`. Register in `main.py` via `app.include_router()`.
- **Models**: Pydantic models in `models/`. Use `Literal` for enums in data models, `str Enum` for internal state.
- **Services**: Business logic in `services/`. Keep thin — one concern per file.
- **DB access**: All queries in `database/connection.py`. Use `aiosqlite.connect(settings.DATABASE_PATH)` per operation (no connection pooling needed for SQLite).
- **Upsert pattern**: After `ON CONFLICT DO UPDATE`, always query the row ID explicitly — `cursor.lastrowid` returns 0 on updates.
- **Async wrappers**: Sync libraries (pdfplumber, instructor) are wrapped with `asyncio.to_thread()`.
- **Retry**: Use `tenacity` with exponential backoff for external calls (HTTP downloads, LLM API).
- **Tests**: pytest + pytest-asyncio. Each async test creates its own tmp_path DB via `monkeypatch`. Run with `uv run python -m pytest tests/ -v`.
- **Imports**: Use relative module paths (`from config import settings`, not absolute filesystem paths).
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

### Pipeline Flow
```
POST /api/efl/process → create_job → BackgroundTask(process_efl_task)
                                          ↓
                          download_pdf (httpx + tenacity retry, SHA256 cache)
                                          ↓
                          extract_text (pdfplumber, classify text vs scanned)
                                          ↓
                          extract_efl_data (LiteLLM + instructor → EFLData)
                                          ↓
                          store_efl_data (SQLite: plans + pricing_tiers + charges)
```

### Key Files
| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, lifespan (init_db + cache dir), CORS, router registration |
| `config.py` | `Settings` class with env vars (DATABASE_PATH, OPENROUTER_API_KEY, LLM_MODEL) |
| `routers/plans.py` | PTC API proxy |
| `routers/efl.py` | EFL process/batch/status/results/validate/cross-validate endpoints |
| `services/downloader.py` | PDF download with retry + content-addressable cache |
| `services/pdf_processor.py` | pdfplumber text extraction + scanned PDF detection |
| `services/llm_client.py` | `instructor.from_litellm(litellm.completion)` factory |
| `services/efl_extractor.py` | System prompt + `_call_llm()` with retry → `EFLData` |
| `services/validator.py` | `sanity_check()`, `compute_confidence()`, `cross_validate_with_ptc()` |
| `database/schema.sql` | DDL for jobs, plans, pricing_tiers, charges + indexes |
| `database/connection.py` | `init_db()`, `store_efl_data()`, `get_plan_data()`, job CRUD |
| `tasks/process_efl.py` | 4-stage pipeline orchestrator (download → extract → parse → store) |

### Database Schema
- **jobs** — background task tracking (status, error, extracted_data JSON)
- **plans** — one row per unique plan (UNIQUE on plan_id + provider + name)
- **pricing_tiers** — price per kWh at 500/1000/2000 kWh (FK to plans)
- **charges** — categorized charges: base, tdu_delivery, tdu_fixed, minimum_usage (FK to plans)
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

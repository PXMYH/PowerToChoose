# Technology Stack

**Project:** Power to Choose - EFL Parser
**Domain:** PDF text extraction and LLM-powered parsing pipeline
**Researched:** 2026-03-21
**Overall Confidence:** HIGH

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

**Recommendation:** Start with **pdfplumber** as primary extractor because EFL documents contain structured tables (pricing tiers, TDU charges) which pdfplumber excels at extracting. Keep pypdf as lightweight fallback.

### HTTP Client

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| httpx | 0.28.1 | PDF download client | Modern HTTP client with both sync and async support, HTTP/2, type annotations. Requests-compatible API but with better async capabilities for concurrent PDF downloads. Required for efficient batch downloading. |

**Why not requests:** requests is synchronous-only and lacks async support. For downloading multiple EFL PDFs concurrently, httpx's async capabilities are essential.

### LLM Integration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| LiteLLM | 1.82.5 | OpenRouter API client | Unified interface to 100+ LLMs including OpenRouter. Handles retries, fallbacks, consistent output format. Use `model="openrouter/<model-name>"` format. Supports streaming and structured outputs. |
| instructor | 1.14.5 | Structured LLM output extraction | **Essential for reliability** — enforces Pydantic models on LLM responses with automatic validation, retry logic, and streaming support. Eliminates manual JSON parsing. Works seamlessly with LiteLLM/OpenRouter. 3M+ monthly downloads, production-proven. |
| Pydantic | 2.12.5 | Data validation and parsing | Type-safe data models for parsed EFL data. v2.x provides major performance improvements and better validation. Required by instructor and FastAPI. |

**Architecture:** Use `instructor` wrapper around `litellm.completion()` to enforce structured outputs. Define Pydantic models for EFL data schema (charges, pricing tiers, terms) and let instructor handle validation/retries.

### Data Storage

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| sqlite3 | Built-in (stdlib) | SQLite database interface | No external installation required. Sufficient for single-file database with straightforward queries. Use Python's built-in module unless ORM benefits outweigh complexity. |

**Why not SQLAlchemy:** SQLAlchemy 2.0.48 is excellent for complex applications, multi-database support, or ORM patterns. For this pipeline's straightforward "parse → store → query" workflow with SQLite-only, the built-in sqlite3 module is simpler and has zero overhead.

### Configuration Management

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pydantic-settings | 2.13.1 | Environment variable management | Type-safe settings with automatic validation. Integrates perfectly with Pydantic models. Supports .env files, cloud secret managers (AWS/Azure/GCP), YAML/TOML configs. Production-stable. |
| python-dotenv | 1.2.2 | .env file loading | Simple, focused library for loading .env files. Use with pydantic-settings for local development. 12-factor app pattern. |

**Pattern:** Define settings class inheriting from `pydantic_settings.BaseSettings`, load .env with python-dotenv, get type-validated config automatically.

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

**Note:** Start without OCR dependencies. Add only if encountering scanned EFL PDFs that text extraction can't handle.

## Installation

### Core Dependencies

```bash
# PDF processing
pip install pdfplumber==0.11.9
pip install pypdf==6.9.1

# HTTP client
pip install httpx==0.28.1

# LLM integration
pip install litellm==1.82.5
pip install instructor==1.14.5
pip install pydantic==2.12.5

# Configuration
pip install pydantic-settings==2.13.1
pip install python-dotenv==1.2.2
```

### Development Dependencies

```bash
pip install pytest==9.0.2
```

### Optional (Add if needed)

```bash
# For scanned PDFs (requires poppler system dependency)
pip install pdf2image==1.17.0
pip install pytesseract==0.3.13
pip install Pillow==12.1.1
```

### Environment Setup

```bash
# .env file
OPENROUTER_API_KEY=your_key_here
OPENROUTER_API_BASE=https://openrouter.ai/api/v1  # optional, defaults to this
```

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

```python
import pdfplumber
from pathlib import Path

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using pdfplumber (primary method)."""
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n\n".join(page.extract_text() or "" for page in pdf.pages)
    return text

def extract_tables_from_pdf(pdf_path: Path) -> list[list[list[str]]]:
    """Extract tables from PDF (pdfplumber's strength)."""
    with pdfplumber.open(pdf_path) as pdf:
        tables = [page.extract_tables() for page in pdf.pages]
    return [t for page_tables in tables for t in page_tables if t]
```

### Pattern 2: Structured LLM Output with Instructor

```python
from pydantic import BaseModel, Field
from litellm import completion
import instructor

# Define structured output model
class EFLCharges(BaseModel):
    base_charge: float = Field(description="Monthly base charge in dollars")
    energy_charge_500: float = Field(description="Energy charge at 500 kWh in cents/kWh")
    energy_charge_1000: float = Field(description="Energy charge at 1000 kWh in cents/kWh")
    energy_charge_2000: float = Field(description="Energy charge at 2000 kWh in cents/kWh")
    early_termination_fee: float | None = Field(description="Early termination fee if applicable")

# Patch LiteLLM with instructor
client = instructor.from_litellm(completion)

# Extract structured data
charges = client(
    model="openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    messages=[
        {"role": "system", "content": "Extract pricing information from EFL document."},
        {"role": "user", "content": f"EFL text:\n\n{pdf_text}"}
    ],
    response_model=EFLCharges,  # instructor enforces this schema
)
# charges is now a validated EFLCharges instance
```

### Pattern 3: Type-Safe Configuration

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openrouter_api_key: str
    openrouter_api_base: str = "https://openrouter.ai/api/v1"
    sqlite_db_path: str = "data/efl_data.db"
    pdf_download_dir: str = "data/pdfs"
    llm_model: str = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
    max_concurrent_downloads: int = 5

# Load settings (reads .env automatically)
settings = Settings()
```

### Pattern 4: Async PDF Download

```python
import httpx
from pathlib import Path
import asyncio

async def download_pdf(url: str, output_path: Path) -> Path:
    """Download PDF asynchronously using httpx."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        output_path.write_bytes(response.content)
    return output_path

async def download_multiple_pdfs(urls: list[str], output_dir: Path):
    """Download multiple PDFs concurrently."""
    tasks = [
        download_pdf(url, output_dir / f"efl_{i}.pdf")
        for i, url in enumerate(urls)
    ]
    return await asyncio.gather(*tasks)
```

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

**Critical:** All packages require Pydantic v2.x. Ensure no legacy dependencies pull in Pydantic v1.

## Sources

**HIGH Confidence:**
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

**MEDIUM Confidence:**
- OpenRouter model availability (nvidia/nemotron) — Could not verify current free models from OpenRouter website. Recommend checking [openrouter.ai/models](https://openrouter.ai/models) directly for current pricing/availability.

---
*Stack research for: PDF text extraction and LLM-powered parsing pipeline*
*Researched: 2026-03-21*
*Confidence: HIGH (all versions verified from official PyPI sources)*

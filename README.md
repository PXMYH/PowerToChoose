# Power to Choose

A better UI for comparing Texas electricity plans from [powertochoose.org](https://www.powertochoose.org).

React + Vite frontend with a FastAPI backend that includes an EFL (Electricity Facts Label) PDF parsing pipeline.

## Features

- **Plan Browser** — Search and filter Texas electricity plans by zip code, usage, and plan type
- **EFL Parser** — Download, extract, and store structured pricing data from provider EFL PDFs using LLM-powered parsing
- **Validation** — Sanity checks, confidence scoring, and cross-validation against Power to Choose API data

## Architecture

```
api/
├── main.py                  # FastAPI app with lifespan, CORS, router registration
├── config.py                # Centralized settings (pydantic-settings, .env)
├── routers/
│   ├── plans.py             # GET /api/plans — proxy to PTC API
│   └── efl.py               # EFL processing, results, validation endpoints
├── services/
│   ├── downloader.py        # PDF download with retry + SHA256 content-addressable cache
│   ├── pdf_processor.py     # PDF classification (text vs scanned) + text extraction
│   ├── llm_client.py        # LiteLLM + instructor client factory
│   ├── efl_extractor.py     # LLM-powered structured extraction with retry
│   └── validator.py         # Sanity checks, confidence scoring, PTC cross-validation
├── models/
│   ├── efl.py               # EFLData, DownloadResult, PDFClassification, etc.
│   ├── job.py               # JobStatus enum and Job model
│   └── validation.py        # ValidationResult, ValidationIssue, CrossValidationResult
├── database/
│   ├── schema.sql           # Normalized schema: jobs, plans, pricing_tiers, charges
│   └── connection.py        # All DB operations (init, CRUD, upsert)
├── tasks/
│   └── process_efl.py       # Background pipeline: download → extract → parse → store
└── tests/                   # 51 tests covering all services and endpoints
```

## API Endpoints

### Plans
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/plans` | Proxy to Power to Choose API (query params: `zip_code`, `estimated_use`, `plan_type`) |

### EFL Processing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/efl/process` | Process a single EFL (`plan_id` + `efl_url`) |
| POST | `/api/efl/process/batch` | Process multiple EFLs in one request |
| GET | `/api/efl/status/{job_id}` | Check processing job status |
| GET | `/api/efl/results/{plan_id}` | Retrieve parsed plan data with pricing tiers and charges |
| GET | `/api/efl/validate/{plan_id}` | Run sanity checks and get confidence score |
| GET | `/api/efl/cross-validate/{plan_id}` | Cross-validate prices against PTC API |

## Local Development

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+

### Backend

```bash
cd api
cp .env.example .env  # Add your OPENROUTER_API_KEY
uv sync
uv run uvicorn main:app --reload --port 8000
```

Runs at `http://localhost:8000`.

#### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | Yes (for EFL parsing) | — | API key from [openrouter.ai](https://openrouter.ai) |
| `DATABASE_PATH` | No | `data/power2choose.db` | SQLite database file path |
| `CACHE_DIR` | No | `data/cache` | PDF download cache directory |
| `LLM_MODEL` | No | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | LLM model for extraction |

#### Running Tests

```bash
cd api
uv run python -m pytest tests/ -v
```

### Frontend

```bash
cd ui
npm install --legacy-peer-deps
npm run dev
```

Runs at `http://localhost:5173`. The Vite dev server proxies `/api` requests to the backend at `localhost:8000`.

## Deployment

### Backend — Render

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect the GitHub repo
3. Set **Root Directory** to `api`
4. Set **Build Command** to `pip install -r requirements.txt`
5. Set **Start Command** to `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Set environment variable `PYTHON_VERSION` = `3.12`
7. Add `OPENROUTER_API_KEY` environment variable
8. Select the **Free** plan and deploy

Render assigns a URL like `https://power2choose-api-xxxx.onrender.com`.

> Free tier spins down after 15 min of inactivity. First request after idle takes ~30s.

### Frontend — GitHub Pages

GitHub Actions builds and deploys the UI automatically on every push to `main`.

To wire it to the Render backend, set a repo variable with the Render URL:

```bash
gh variable set VITE_API_URL --body "https://YOUR-RENDER-URL.onrender.com"
```

Then re-run the workflow (or push a commit) so the frontend rebuilds with the API URL baked in.

The site will be live at `https://<username>.github.io/PowerToChoose/`.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite |
| Backend | FastAPI + uvicorn |
| PDF Processing | pdfplumber |
| LLM Integration | LiteLLM + instructor (OpenRouter) |
| Database | SQLite (aiosqlite) |
| HTTP Client | httpx |
| Config | pydantic-settings |
| Testing | pytest + pytest-asyncio |

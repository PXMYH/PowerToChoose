# Power to Choose

A better UI for comparing Texas electricity plans from [powertochoose.org](https://www.powertochoose.org).

React + Vite frontend with a FastAPI backend proxy.

## Local Development

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+

### Backend

```bash
cd api
uv sync
uv run uvicorn main:app --reload --port 8000
```

Runs at `http://localhost:8000`. The single endpoint is `GET /api/plans?zip_code=78665&estimated_use=1000&plan_type=`.

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
7. Select the **Free** plan and deploy

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

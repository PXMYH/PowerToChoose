from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database.connection import init_db
from routers.plans import router as plans_router
from routers.efl import router as efl_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.CACHE_DIR).mkdir(parents=True, exist_ok=True)
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(plans_router)
app.include_router(efl_router)

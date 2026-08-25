from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app import seed
from app.api import (
    auth,
    changes,
    crawls,
    dashboard,
    demo,
    impact,
    notifications,
    regulations,
    review,
    sources,
    subscriptions,
)
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.demo_site_dir).mkdir(parents=True, exist_ok=True)
    seed.seed()
    yield


Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
Path(settings.demo_site_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sources.router)
app.include_router(crawls.router)
app.include_router(regulations.router)
app.include_router(changes.router)
app.include_router(review.router)
app.include_router(impact.router)
app.include_router(subscriptions.router)
app.include_router(notifications.router)
app.include_router(dashboard.router)
app.include_router(demo.router)

app.mount("/demo-site", StaticFiles(directory=settings.demo_site_dir, html=True), name="demo_site")


@app.get("/robots.txt", response_class=PlainTextResponse)
def root_robots():
    robots_path = Path(settings.demo_site_dir) / "robots.txt"
    if robots_path.exists():
        return robots_path.read_text(encoding="utf-8")
    return "User-agent: *\nAllow: /\n"


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "crawl_eager": settings.crawl_eager}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import Base, engine
from app.routers import (
    sources, crawl_runs, regulations, changes, reviews,
    impact, subscriptions, notifications, dashboard
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(sources.router)
app.include_router(crawl_runs.router)
app.include_router(regulations.router)
app.include_router(changes.router)
app.include_router(reviews.router)
app.include_router(impact.router)
app.include_router(subscriptions.router)
app.include_router(notifications.router)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }

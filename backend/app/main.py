from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    changes,
    dashboard,
    regulations,
    reviews,
    runs,
    sources,
    subscriptions,
)
from app.core.config import settings
from app.core.database import Base, engine
from app.models import models  # noqa: F401 - ensure models are registered


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create tables on startup (demo-friendly; use Alembic for real migrations)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = settings.api_prefix
app.include_router(auth.router, prefix=api)
app.include_router(sources.router, prefix=api)
app.include_router(runs.router, prefix=api)
app.include_router(changes.router, prefix=api)
app.include_router(reviews.router, prefix=api)
app.include_router(regulations.router, prefix=api)
app.include_router(regulations.docs_router, prefix=api)
app.include_router(subscriptions.router, prefix=api)
app.include_router(subscriptions.notif_router, prefix=api)
app.include_router(dashboard.router, prefix=api)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}

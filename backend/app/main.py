from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text

from app.api import api_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import User, utcnow
from app.security import hash_password


def _ensure_change_attachment_columns() -> None:
    """轻量自动迁移：老库 changes 表缺附件版本外键列时用原生 SQL 补齐（sqlite/PG 通用）。"""
    inspector = inspect(engine)
    if "changes" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("changes")}
    ddl = {
        "old_attachment_id": "ALTER TABLE changes ADD COLUMN old_attachment_id INTEGER REFERENCES attachments(id)",
        "new_attachment_id": "ALTER TABLE changes ADD COLUMN new_attachment_id INTEGER REFERENCES attachments(id)",
    }
    with engine.begin() as conn:
        for column, stmt in ddl.items():
            if column not in existing:
                conn.execute(text(stmt))


def _seed_default_admin() -> None:
    """users 表为空时播种默认管理员 admin / admin123。"""
    with SessionLocal() as session:
        if session.scalar(select(User.id).limit(1)) is not None:
            return
        session.add(User(username="admin", password_hash=hash_password("admin123"), role="admin", created_at=utcnow()))
        session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.snapshot_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _ensure_change_attachment_columns()
    _seed_default_admin()
    yield


app = FastAPI(title="法规变更情报与影响研判平台", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

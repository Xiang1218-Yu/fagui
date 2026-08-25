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


def _ensure_user_columns() -> None:
    """轻量自动迁移：老库 users 表缺 must_change_password 列时补齐（sqlite/PG 通用）。"""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("users")}
    ddl = {
        "must_change_password": "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT FALSE",
    }
    with engine.begin() as conn:
        for column, stmt in ddl.items():
            if column not in existing:
                conn.execute(text(stmt))


def _seed_default_admin() -> None:
    """users 表为空时播种默认管理员；初始密码可由 ADMIN_INITIAL_PASSWORD 指定，默认 admin123。

    播种的 admin 一律 must_change_password=True，首次登录后强制改密。
    """
    with SessionLocal() as session:
        if session.scalar(select(User.id).limit(1)) is not None:
            return
        initial_password = settings.admin_initial_password or "admin123"
        session.add(
            User(
                username="admin",
                password_hash=hash_password(initial_password),
                role="admin",
                must_change_password=True,
                created_at=utcnow(),
            )
        )
        session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.snapshot_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _ensure_change_attachment_columns()
    _ensure_user_columns()
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

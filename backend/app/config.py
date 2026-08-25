import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "法规变更情报与影响研判平台"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/regulatory_intel"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

    SNAPSHOT_STORAGE_PATH: str = os.getenv("SNAPSHOT_STORAGE_PATH", "./data/snapshots")
    ATTACHMENT_STORAGE_PATH: str = os.getenv("ATTACHMENT_STORAGE_PATH", "./data/attachments")

    MAX_CRAWL_DEPTH: int = int(os.getenv("MAX_CRAWL_DEPTH", "2"))
    CRAWL_DELAY_SECONDS: float = float(os.getenv("CRAWL_DELAY_SECONDS", "2.0"))
    CRAWL_TIMEOUT: int = int(os.getenv("CRAWL_TIMEOUT", "30"))
    MAX_ATTACHMENT_SIZE_MB: int = int(os.getenv("MAX_ATTACHMENT_SIZE_MB", "50"))
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "RegulatoryIntelBot/1.0 (+compliance research; respects robots.txt)"
    )

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
